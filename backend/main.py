from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
from config import anthropic_client, cohere_client, get_db_session

app = FastAPI()

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatQuery(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str
    context: List[Dict]

def generate_embedding(text):
    """Generate embedding at runtime using Cohere"""
    response = cohere_client.embed(
        model="embed-english-v3.0",
        texts=[text],
        embedding_types=["float"],
        input_type="search_query"
    )
    return response.embeddings.float[0]

@app.post("/api/chat", response_model=ChatResponse)
async def chat(query: ChatQuery):
    """Answer questions using GraphRAG with runtime embeddings"""
    
    # Generate embedding for the question at runtime
    query_embedding = generate_embedding(query.question)
    
    # Get all nodes and generate embeddings at runtime for comparison
    with get_db_session() as session:
        # First, get all entities
        all_nodes_result = session.run("""
            MATCH (e:Entity)
            RETURN e.id as id, e.name as name, e.description as description
            LIMIT 50
        """)
        
        nodes = []
        for record in all_nodes_result:
            node_text = f"{record['name']}: {record['description']}"
            node_embedding = generate_embedding(node_text)
            
            # Calculate cosine similarity
            similarity = cosine_similarity(query_embedding, node_embedding)
            
            if similarity > 0.7:  # Threshold for relevance
                nodes.append({
                    'id': record['id'],
                    'name': record['name'],
                    'description': record['description'],
                    'similarity': similarity
                })
        
        # Sort by similarity and take top 5
        nodes.sort(key=lambda x: x['similarity'], reverse=True)
        top_nodes = nodes[:5]
        
        # Get relationships for top nodes
        context = []
        for node in top_nodes:
            rel_result = session.run("""
                MATCH (e:Entity {id: $id})
                OPTIONAL MATCH (e)-[r]-(connected:Entity)
                RETURN collect(DISTINCT {
                    type: type(r),
                    connected: connected.name,
                    connected_desc: connected.description
                }) as relationships
            """, {'id': node['id']})
            
            relationships = rel_result.single()['relationships']
            context.append({
                'entity': node['name'],
                'description': node['description'],
                'relationships': relationships
            })
    
    # Build context string
    context_str = "Knowledge Graph Context:\n"
    for item in context:
        context_str += f"\n{item['entity']}: {item['description']}"
        for rel in item['relationships']:
            if rel['connected']:
                context_str += f"\n  - {rel['type']} -> {rel['connected']}"
    
    # Generate answer using Claude 4 Sonnet
    response = anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system="You are a business consultant answering questions based on mental models from the knowledge graph.",
        messages=[
            {"role": "user", "content": f"{context_str}\n\nQuestion: {query.question}\n\nAnswer based on the context provided:"}
        ]
    )
    
    return ChatResponse(
        answer=response.content[0].text,
        context=context
    )

@app.get("/api/graph")
async def get_graph():
    """Get graph data for visualization"""
    with get_db_session() as session:
        # Get all entities and relationships
        result = session.run("""
            MATCH (e:Entity)
            OPTIONAL MATCH (e)-[r]-(connected:Entity)
            RETURN e.id as id, e.name as name, e.type as type, 
                   e.description as description,
                   collect(DISTINCT {
                       from: e.id,
                       to: connected.id,
                       type: type(r)
                   }) as relationships
            LIMIT 100
        """)
        
        nodes = []
        edges = []
        seen_nodes = set()
        
        for record in result:
            node_id = record['id']
            
            if node_id not in seen_nodes:
                nodes.append({
                    'id': node_id,
                    'label': record['name'] or node_id,
                    'type': record['type'],
                    'description': record['description']
                })
                seen_nodes.add(node_id)
            
            for rel in record['relationships']:
                if rel['to'] and rel['from']:
                    edge_key = f"{rel['from']}-{rel['to']}-{rel['type']}"
                    edges.append({
                        'from': rel['from'],
                        'to': rel['to'],
                        'label': rel['type']
                    })
        
        return {'nodes': nodes, 'edges': edges}

@app.get("/api/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors"""
    import numpy as np
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0
    
    return dot_product / (norm1 * norm2)