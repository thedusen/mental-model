from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import logging
import os
import asyncio
import json
from config import anthropic_client, cohere_client, get_db_session
from keep_warm import keep_warm_service
from prompts import SYSTEM_PROMPT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Mental Model Knowledge Graph API",
    description="A Neo4j-based knowledge graph system for building and exploring mental models",
    version="1.0.0"
)

# CORS - Allow your frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for debugging
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Simple health check for deployment platforms
@app.get("/health")
async def health_check():
    try:
        with get_db_session() as session:
            session.run("RETURN 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

# Startup event to begin keep-warm service (only for Aura deployments)
@app.on_event("startup")
async def startup_event():
    logger.info("Mental Model API starting up...")
    
    # Start keep-warm service if using Neo4j Aura
    if os.getenv("NEO4J_URI", "").startswith("neo4j+s://"):
        logger.info("Detected Neo4j Aura connection - starting keep-warm service")
        asyncio.create_task(keep_warm_service.start_keep_warm_loop())
    else:
        logger.info("Using local/Railway Neo4j - keep-warm service not needed")

# Shutdown event to stop keep-warm service
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Mental Model API shutting down...")
    await keep_warm_service.stop_keep_warm_loop()
    logger.info("Application shutdown completed")

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class SelectedNode(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    theme: Optional[str] = None
    labels: List[str] = []

class ChatQuery(BaseModel):
    question: str
    conversation_history: List[ChatMessage] = []
    selected_node: Optional[SelectedNode] = None

class TokensUsed(BaseModel):
    input: Optional[int]
    output: Optional[int]

class ChatResponse(BaseModel):
    answer: str
    context: List[Dict]
    conversation_length: int
    tokens_used: TokensUsed

def generate_query_embedding(text):
    # CORRECTED: Specify embedding_types and access the .float attribute.
    response = cohere_client.embed(
        texts=[text], model="embed-english-v3.0", input_type="search_query", embedding_types=["float"]
    )
    return response.embeddings.float[0]  # type: ignore

@app.post("/api/chat", response_model=ChatResponse)
async def chat(query: ChatQuery):
    try:
        # Generate embedding for the current question
        embedding = generate_query_embedding(query.question)
        
        # Retrieve relevant context from knowledge graph
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

        # Build knowledge graph context string
        if context_data:
            context_str = "Knowledge Graph Context:\n" + "\n".join(
                [f"- {item['entity']}: {item['description']}" for item in context_data]
            )
        else:
            context_str = "No specific knowledge graph context found for this question."

        # Build conversation messages with rolling window (last 15 messages)
        messages = []
        
        # Add conversation history (limit to last 15 messages)
        recent_history = query.conversation_history[-15:]
        
        for msg in recent_history:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add selected node context if available
        selected_node_context = ""
        if query.selected_node:
            selected_node_context = f"\n\nCurrently Selected Node:\n- Name: {query.selected_node.name}\n- Type: {query.selected_node.type}\n- Description: {query.selected_node.description}\n- Theme: {query.selected_node.theme}\n- Labels: {', '.join(query.selected_node.labels) if query.selected_node.labels else 'None'}"
        
        # Add current question with knowledge graph context and selected node
        current_message = f"{context_str}{selected_node_context}\n\nQuestion: {query.question}"
        messages.append({
            "role": "user", 
            "content": current_message
        })

        # Call Claude with conversation history and prompt caching
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,  # Increased for large context windows and extended responses
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"}  # Cache the long system prompt
                }
            ],
            messages=messages,
            stream=False  # We'll implement streaming in a separate endpoint
        )
        
        answer_text = ""
        for block in response.content:
            if block.type == 'text':
                answer_text = block.text
                break
                
        return {
            "answer": answer_text, 
            "context": context_data,
            "conversation_length": len(recent_history) + 1,  # Include current message
            "tokens_used": {
                "input": response.usage.input_tokens if hasattr(response, 'usage') else None,
                "output": response.usage.output_tokens if hasattr(response, 'usage') else None
            }
        }
        
    except Exception as e:
        logger.error(f"Error in /api/chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

@app.post("/api/chat/stream")
async def chat_stream(query: ChatQuery):
    """Streaming chat endpoint for real-time responses"""
    try:
        # Generate embedding for the current question
        embedding = generate_query_embedding(query.question)
        
        # Retrieve relevant context from knowledge graph
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

        # Build knowledge graph context string
        if context_data:
            context_str = "Knowledge Graph Context:\n" + "\n".join(
                [f"- {item['entity']}: {item['description']}" for item in context_data]
            )
        else:
            context_str = "No specific knowledge graph context found for this question."

        # Build conversation messages with rolling window (last 15 messages)
        messages = []
        
        # Add conversation history (limit to last 15 messages)
        recent_history = query.conversation_history[-15:]
        
        for msg in recent_history:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add selected node context if available
        selected_node_context = ""
        if query.selected_node:
            selected_node_context = f"\n\nCurrently Selected Node:\n- Name: {query.selected_node.name}\n- Type: {query.selected_node.type}\n- Description: {query.selected_node.description}\n- Theme: {query.selected_node.theme}\n- Labels: {', '.join(query.selected_node.labels) if query.selected_node.labels else 'None'}"
        
        # Add current question with knowledge graph context and selected node
        current_message = f"{context_str}{selected_node_context}\n\nQuestion: {query.question}"
        messages.append({
            "role": "user", 
            "content": current_message
        })

        async def generate_stream():
            try:
                # Send initial metadata
                yield f"data: {json.dumps({'type': 'metadata', 'context': context_data})}\n\n"
                
                # Call Claude with streaming enabled
                stream = anthropic_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=8192,
                    system=[
                        {
                            "type": "text",
                            "text": SYSTEM_PROMPT,
                            "cache_control": {"type": "ephemeral"}
                        }
                    ],
                    messages=messages,
                    stream=True
                )
                
                full_response = ""
                for event in stream:
                    if event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            text_chunk = event.delta.text
                            full_response += text_chunk
                            # Send each text chunk to the client
                            yield f"data: {json.dumps({'type': 'content', 'text': text_chunk})}\n\n"
                    
                    elif event.type == "message_stop":
                        # Send completion signal with full response
                        yield f"data: {json.dumps({'type': 'done', 'full_response': full_response})}\n\n"
                        break
                    
                    elif event.type == "error":
                        logger.error(f"Error in stream: {event.error}")
                        yield f"data: {json.dumps({'type': 'error', 'message': str(event.error)})}\n\n"
                        break
                        
            except Exception as e:
                logger.error(f"Error in streaming: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'message': 'An error occurred while streaming the response.'})}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except Exception as e:
        logger.error(f"Error in /api/chat/stream: {e}", exc_info=True)
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
                e.content as content,
                e.theme as theme,
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
                null as content,
                null as theme,
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
                    'description': record['description'] or '',
                    'content': record['content'] or '',
                    'theme': record['theme'] or ''
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
