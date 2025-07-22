from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import logging
import os
import asyncio
import json
import time
from functools import lru_cache
from config import anthropic_client, cohere_client, get_db_session
from keep_warm import keep_warm_service
from prompts import SYSTEM_PROMPT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simple in-memory cache for graph data
_graph_cache = {"data": None, "timestamp": 0}
CACHE_TTL = 300  # 5 minutes in seconds

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

# Add Gzip compression for better performance
app.add_middleware(GZipMiddleware, minimum_size=1000)

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

class ChatContextNode(BaseModel):
    """Represents a node explicitly added to chat context by the user"""
    id: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    theme: Optional[str] = None
    labels: List[str] = []

class ChatQuery(BaseModel):
    question: str
    conversation_history: List[ChatMessage] = []
    # DEPRECATED: selected_node - keeping for backward compatibility but not using
    selected_node: Optional[ChatContextNode] = None
    # NEW: chat_context_node - only used when explicitly set by user
    chat_context_node: Optional[ChatContextNode] = None

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
        
        # Add chat context node ONLY if explicitly provided (user clicked "Chat with this node")
        chat_context_str = ""
        if query.chat_context_node:
            chat_context_str = f"\n\nChat Context Node (User explicitly added this for focused discussion):\n- Name: {query.chat_context_node.name}\n- Type: {query.chat_context_node.type}\n- Description: {query.chat_context_node.description}\n- Theme: {query.chat_context_node.theme}\n- Labels: {', '.join(query.chat_context_node.labels) if query.chat_context_node.labels else 'None'}"
            logger.info(f"Chat context node added: {query.chat_context_node.name}")
        else:
            logger.info("No chat context node provided - proceeding with general knowledge graph context only")
        
        # Add current question with knowledge graph context and optional chat context node
        current_message = f"{context_str}{chat_context_str}\n\nQuestion: {query.question}"
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
        
        # Add chat context node ONLY if explicitly provided
        chat_context_str = ""
        if query.chat_context_node:
            chat_context_str = f"\n\nChat Context Node (User explicitly added this for focused discussion):\n- Name: {query.chat_context_node.name}\n- Type: {query.chat_context_node.type}\n- Description: {query.chat_context_node.description}\n- Theme: {query.chat_context_node.theme}\n- Labels: {', '.join(query.chat_context_node.labels) if query.chat_context_node.labels else 'None'}"
            logger.info(f"Streaming chat context node added: {query.chat_context_node.name}")
        else:
            logger.info("Streaming: No chat context node provided")
        
        # Add current question with knowledge graph context and optional chat context node
        current_message = f"{context_str}{chat_context_str}\n\nQuestion: {query.question}"
        messages.append({
            "role": "user", 
            "content": current_message
        })

        async def generate():
            try:
                # Send metadata first
                yield f"data: {json.dumps({'type': 'metadata', 'context': context_data})}\n\n"
                
                # Stream response from Claude
                with anthropic_client.messages.stream(
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
                ) as stream:
                    for text in stream.text_stream:
                        yield f"data: {json.dumps({'type': 'content', 'text': text})}\n\n"
                
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                
            except Exception as e:
                logger.error(f"Error in streaming: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            }
        )
        
    except Exception as e:
        logger.error(f"Error in /api/chat/stream: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred during streaming.")

@app.get("/api/graph")
async def get_graph():
    # Check cache first
    current_time = time.time()
    if (_graph_cache["data"] is not None and 
        current_time - _graph_cache["timestamp"] < CACHE_TTL):
        logger.info("Returning cached graph data")
        return JSONResponse(
            content=_graph_cache["data"],
            headers={"Cache-Control": "public, max-age=300"}
        )
    
    logger.info("Cache miss - fetching fresh graph data")
    with get_db_session() as session:
        # Get ALL nodes - both Entity nodes and standalone nodes (optimized)
        nodes_result = session.run("""
            MATCH (n)
            WHERE n:Entity OR n:Theme OR n:Pattern OR n:Example OR n:Principle OR n:Expert OR n:MentalModel
            RETURN 
                CASE 
                    WHEN n:Theme THEN n.name 
                    WHEN n.id IS NOT NULL THEN n.id
                    WHEN n.name IS NOT NULL THEN n.name
                    ELSE toString(id(n))
                END as id,
                CASE 
                    WHEN n:Theme THEN 'Theme'
                    WHEN n:Entity AND n.category IS NOT NULL THEN n.category
                    WHEN n:Pattern THEN 'Pattern'
                    WHEN n:Example THEN 'Example' 
                    WHEN n:Principle THEN 'Principle'
                    WHEN n:Expert THEN 'Expert'
                    WHEN n:MentalModel THEN 'MentalModel'
                    ELSE 'Entity'
                END as type,
                COALESCE(n.description, '') as description,
                COALESCE(n.content, '') as content,
                COALESCE(n.theme, '') as theme
        """)
        
        # Get ALL relationships separately - optimized with constraints
        edges_result = session.run("""
            MATCH (a)-[r]-(b)
            WHERE a <> b 
            AND (a:Entity OR a:Theme OR a:Pattern OR a:Example OR a:Principle OR a:Expert OR a:MentalModel)
            AND (b:Entity OR b:Theme OR b:Pattern OR b:Example OR b:Principle OR b:Expert OR b:MentalModel)
            RETURN 
                CASE 
                    WHEN a:Theme THEN a.name 
                    WHEN a.id IS NOT NULL THEN a.id
                    WHEN a.name IS NOT NULL THEN a.name
                    ELSE toString(id(a))
                END as from_node,
                CASE 
                    WHEN b:Theme THEN b.name 
                    WHEN b.id IS NOT NULL THEN b.id
                    WHEN b.name IS NOT NULL THEN b.name
                    ELSE toString(id(b))
                END as to_node,
                type(r) as rel_type,
                startNode(r) = a as is_outgoing
        """)
        
        nodes, edges = [], []
        seen_nodes = set()
        
        # Process nodes
        for record in nodes_result:
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
        
        # Process edges - no restrictions, include all relationships
        edge_set = set()  # To avoid duplicates
        for record in edges_result:
            from_node, to_node, rel_type, is_outgoing = record['from_node'], record['to_node'], record['rel_type'], record['is_outgoing']
            if from_node and to_node and from_node in seen_nodes and to_node in seen_nodes:
                # Use the actual direction from the database
                if is_outgoing:
                    # a->b: from_node is correct
                    actual_from, actual_to = from_node, to_node
                else:
                    # b->a: swap direction
                    actual_from, actual_to = to_node, from_node
                
                edge_key = (actual_from, actual_to, rel_type)
                if edge_key not in edge_set:
                    edges.append({
                        'from': actual_from,
                        'to': actual_to, 
                        'label': rel_type
                    })
                    edge_set.add(edge_key)
        
        # Cache the result
        graph_data = {"nodes": nodes, "edges": edges}
        _graph_cache["data"] = graph_data
        _graph_cache["timestamp"] = current_time
        logger.info(f"Cached graph data: {len(nodes)} nodes, {len(edges)} edges")
        
        return JSONResponse(
            content=graph_data,
            headers={"Cache-Control": "public, max-age=300"}
        )

class SearchResult(BaseModel):
    id: str
    type: str
    description: str
    theme: Optional[str] = None
    score: float

class SearchResponse(BaseModel):
    results: List[SearchResult]
    query: str
    total_count: int
    execution_time_ms: int

@app.get("/api/search", response_model=SearchResponse)
async def search_nodes(
    q: str,
    limit: int = 10,
    threshold: float = 0.3,
    include_themes: bool = False
):
    """
    Semantic search across knowledge graph nodes using vector similarity.
    
    Args:
        q: Search query string
        limit: Maximum number of results (max 50)
        threshold: Minimum similarity score (0.0-1.0)
        include_themes: Whether to include Theme nodes in results
    """
    try:
        import time
        start_time = time.time()
        
        # Validate parameters
        if not q or len(q.strip()) < 2:
            raise HTTPException(status_code=400, detail="Query must be at least 2 characters long")
        
        limit = min(max(1, limit), 50)  # Clamp between 1 and 50
        threshold = max(0.0, min(1.0, threshold))  # Clamp between 0 and 1
        
        # Generate embedding for search query
        embedding = generate_query_embedding(q.strip())
        
        # Build search query based on include_themes parameter
        if include_themes:
            # Search both Entity and Theme nodes
            search_query = """
                // Search Entity nodes
                CALL db.index.vector.queryNodes('entity_embeddings', $limit, $embedding) YIELD node, score
                WHERE score > $threshold AND node:Entity
                WITH node, score, 'Entity' as node_type
                RETURN node.id as id, 
                       COALESCE(node.category, 'Uncategorized') as type,
                       node.description as description,
                       node.theme as theme,
                       score,
                       node_type
                ORDER BY score DESC
                LIMIT $limit
            """
        else:
            # Search only Entity nodes (default for better relevance)
            search_query = """
                CALL db.index.vector.queryNodes('entity_embeddings', $limit, $embedding) YIELD node, score
                WHERE score > $threshold AND node:Entity
                RETURN node.id as id,
                       COALESCE(node.category, 'Uncategorized') as type, 
                       node.description as description,
                       node.theme as theme,
                       score
                ORDER BY score DESC
                LIMIT $limit
            """
        
        # Execute search
        with get_db_session() as session:
            result = session.run(search_query, {
                'embedding': embedding,
                'limit': limit,
                'threshold': threshold
            })
            
            search_results = []
            for record in result:
                search_results.append(SearchResult(
                    id=record['id'],
                    type=record['type'],
                    description=record['description'] or '',
                    theme=record.get('theme'),
                    score=record['score']
                ))
        
        execution_time = int((time.time() - start_time) * 1000)
        
        logger.info(f"Search query '{q}' returned {len(search_results)} results in {execution_time}ms")
        
        return SearchResponse(
            results=search_results,
            query=q.strip(),
            total_count=len(search_results),
            execution_time_ms=execution_time
        )
        
    except Exception as e:
        logger.error(f"Error in /api/search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Search request failed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
