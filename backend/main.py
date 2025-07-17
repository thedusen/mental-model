from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
from config import anthropic_client, cohere_client, get_db_session

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

@app.get("/api/graph")
async def get_graph():
    with get_db_session() as session:
        result = session.run("""
            MATCH (e:Entity)
            OPTIONAL MATCH (e)-[r]-(c:Entity)
            RETURN e.id as id, e.type as type, e.description as description,
                   collect(DISTINCT {from: e.id, to: c.id, type: type(r)}) as relationships
            LIMIT 100
        """)
        nodes, edges = [], []
        seen_nodes = set()
        for record in result:
            if record['id'] not in seen_nodes:
                nodes.append({'id': record['id'], 'label': record['id'], 'type': record['type'], 'description': record['description']})
                seen_nodes.add(record['id'])
            for rel in record['relationships']:
                if rel['to'] and rel['from']:
                    edges.append({'from': rel['from'], 'to': rel['to'], 'label': rel['type']})
        return {'nodes': nodes, 'edges': edges}
