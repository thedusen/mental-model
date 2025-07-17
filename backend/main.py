from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import logging
from config import anthropic_client, cohere_client, get_db_session

logging.basicConfig(level=logging.INFO)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatQuery(BaseModel):
    question: str

def generate_query_embedding(text):
    # CORRECTED: Specify embedding_types and access the .float attribute.
    response = cohere_client.embed(
        texts=[text], model="embed-english-v3.0", input_type="search_query", embedding_types=["float"]
    )
    return response.embeddings.float[0]  # type: ignore

@app.post("/api/chat")
async def chat(query: ChatQuery):
    try:
        embedding = generate_query_embedding(query.question)
        with get_db_session() as session:
            result = session.run("""
                CALL db.index.vector.queryNodes('entity_embeddings', 5, $embedding) YIELD node, score
                WHERE score > 0.5
                WITH node
                OPTIONAL MATCH (node)-[r]-(connected:Entity)
                RETURN node.id as entity, node.description as description,
                       collect(DISTINCT {
                           type: type(r),
                           connected: connected.id
                       }) as relationships
            """, {'embedding': embedding})
            context_data = [dict(record) for record in result]

        if not context_data:
            return {"answer": "I couldn't find any relevant information in the knowledge graph to answer your question.", "context": []}

        context_str = "Knowledge Graph Context:\n" + "\n".join(
            [f"- {item['entity']}: {item['description']}" for item in context_data]
        )

        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system="You are a business consultant answering questions based on mental models from the provided knowledge graph context.",
            messages=[
                {"role": "user", "content": f"{context_str}\n\nQuestion: {query.question}\n\nAnswer based on the context provided:"}
            ]
        )
        
        answer_text = ""
        for block in response.content:
            if block.type == 'text':
                answer_text = block.text
                break
                
        return {"answer": answer_text, "context": context_data}
    except Exception as e:
        logging.error(f"Error in /api/chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

@app.get("/api/graph")
async def get_graph():
    with get_db_session() as session:
        # Get all Entity and Theme nodes with their relationships
        result = session.run("""
            // Get all Entity nodes with their categories
            MATCH (e:Entity)
            OPTIONAL MATCH (e)-[r1:BELONGS_TO]->(t:Theme)
            OPTIONAL MATCH (e)-[r2]-(other:Entity)
            RETURN 
                'Entity' as node_class,
                e.id as id, 
                COALESCE(e.category, 'Uncategorized') as type, 
                e.description as description,
                collect(DISTINCT {from: e.id, to: t.name, type: 'BELONGS_TO'}) + 
                collect(DISTINCT {from: e.id, to: other.id, type: type(r2)}) + 
                collect(DISTINCT {from: other.id, to: e.id, type: type(r2)}) as relationships
            
            UNION ALL
            
            // Get all Theme nodes
            MATCH (t:Theme)
            RETURN 
                'Theme' as node_class,
                t.name as id,
                'Theme' as type,
                t.description as description,
                [] as relationships
        """)
        
        nodes, edges = [], []
        seen_nodes = set()
        
        # First pass: collect all nodes
        all_records = list(result)
        for record in all_records:
            if record['id'] not in seen_nodes:
                nodes.append({
                    'id': record['id'], 
                    'label': record['id'],  # Use ID as label
                    'type': record['type'],
                    'description': record['description'] or ''
                })
                seen_nodes.add(record['id'])
        
        # Second pass: collect valid relationships (only between existing nodes)
        edge_set = set()  # To avoid duplicates
        for record in all_records:
            for rel in record['relationships']:
                if rel and rel.get('from') and rel.get('to'):
                    from_node, to_node = rel['from'], rel['to']
                    if from_node in seen_nodes and to_node in seen_nodes:
                        edge_key = (from_node, to_node, rel.get('type', ''))
                        if edge_key not in edge_set:
                            edges.append({
                                'from': from_node,
                                'to': to_node, 
                                'label': rel.get('type', 'RELATED')
                            })
                            edge_set.add(edge_key)
        
        return {"nodes": nodes, "edges": edges}
