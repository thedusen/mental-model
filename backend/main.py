from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional, Any, Union
import logging
import os
import asyncio
import json
import time
import numpy as np
from functools import lru_cache
from config import anthropic_client, cohere_client, get_db_session
from keep_warm import keep_warm_service
from prompts import SYSTEM_PROMPT
from supabase_client import supabase_service
from zep_memory import zep_memory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simple in-memory cache for graph data
_graph_cache = {"data": None, "timestamp": 0}
CACHE_TTL = 300  # 5 minutes in seconds

# Business profile cache - 24 hour TTL since profiles change infrequently
_business_profile_cache = {}
BUSINESS_PROFILE_CACHE_TTL = 86400  # 24 hours in seconds


def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors"""
    try:
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    except Exception:
        return 0.0


async def get_cached_business_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """Get business profile from cache or fetch from Zep using business data session"""
    current_time = time.time()
    cache_key = f"business_profile_{user_id}"

    # Check cache first
    if cache_key in _business_profile_cache:
        cached_data = _business_profile_cache[cache_key]
        if current_time - cached_data["timestamp"] < BUSINESS_PROFILE_CACHE_TTL:
            logger.debug(f"Using cached business profile for user {user_id}")
            return cached_data["data"]

    # Fetch from Zep using the dedicated business profile method
    try:
        business_profile = zep_memory.get_business_profile(user_id)

        if business_profile:
            # Cache the result
            _business_profile_cache[cache_key] = {
                "data": business_profile,
                "timestamp": current_time,
            }
            logger.debug(f"Cached business profile for user {user_id}")
            return business_profile

    except Exception as e:
        logger.warning(f"Failed to fetch business profile for user {user_id}: {e}")

    return None


def get_relevant_business_elements(
    query: str, business_profile: Dict[str, Any], max_elements: int = 5
) -> Dict[str, Any]:
    """Select most relevant business profile elements based on query similarity"""
    if not business_profile:
        return {}

    try:
        # Generate embedding for the query
        query_embedding = generate_query_embedding(query)

        relevant_elements = {}

        # Define business context categories for smarter matching
        strategic_keywords = [
            "challenge",
            "goal",
            "strategy",
            "growth",
            "vision",
            "mission",
            "success",
            "objectives",
        ]
        operational_keywords = [
            "team",
            "employees",
            "operations",
            "process",
            "workflow",
            "capacity",
            "efficiency",
        ]
        financial_keywords = [
            "revenue",
            "profit",
            "cost",
            "budget",
            "financial",
            "money",
            "sales",
            "pricing",
        ]
        industry_keywords = [
            "industry",
            "market",
            "competition",
            "customer",
            "client",
            "service",
            "product",
        ]

        query_lower = query.lower()

        for key, value in business_profile.items():
            if not value or not isinstance(value, str):
                continue

            # Calculate semantic similarity
            element_text = f"{key.replace('_', ' ')}: {value}"
            try:
                element_embedding = generate_query_embedding(element_text)
                similarity = cosine_similarity(query_embedding, element_embedding)
            except Exception:
                similarity = 0.0

            # Boost relevance based on keyword matching
            relevance_boost = 0.0
            if any(keyword in query_lower for keyword in strategic_keywords):
                if key in [
                    "biggest_challenge",
                    "main_business_goal",
                    "success_metrics",
                    "primary_goals",
                ]:
                    relevance_boost = 0.2
            elif any(keyword in query_lower for keyword in operational_keywords):
                if key in [
                    "employee_count",
                    "team_capacity_for_growth",
                    "business_operations_when_away",
                    "work_similarity_to_team",
                ]:
                    relevance_boost = 0.2
            elif any(keyword in query_lower for keyword in financial_keywords):
                if key in ["revenue_range", "profitability_confidence"]:
                    relevance_boost = 0.2
            elif any(keyword in query_lower for keyword in industry_keywords):
                if key in ["industry"]:
                    relevance_boost = 0.2

            final_score = similarity + relevance_boost

            # Only include elements above relevance threshold
            if final_score > 0.25:  # Lowered threshold to be more inclusive
                relevant_elements[key] = {
                    "value": value,
                    "relevance_score": final_score,
                    "similarity": similarity,
                    "boost": relevance_boost,
                }

        # Return top elements sorted by relevance
        sorted_elements = dict(
            sorted(
                relevant_elements.items(),
                key=lambda x: x[1]["relevance_score"],
                reverse=True,
            )[:max_elements]
        )

        logger.debug(
            f"Selected {len(sorted_elements)} relevant business elements for query: {query[:50]}..."
        )
        return sorted_elements

    except Exception as e:
        logger.warning(f"Error in business element selection: {e}")
        return {}


async def get_optimized_user_context(user_id: str, session_id: str, query: str) -> str:
    """Get optimized user context combining business profile and conversational memory"""
    context_parts = []

    try:
        # Get business profile context using direct entity access (more reliable)
        from zep_memory import zep_service
        
        questionnaire_context = await zep_service.get_questionnaire_context_direct(user_id, query)
        if questionnaire_context:
            context_parts.append(questionnaire_context)
            logger.debug(f"Added direct questionnaire context ({len(questionnaire_context)} chars)")
        else:
            # Fallback to old regex-based method if direct access fails
            business_profile = await get_cached_business_profile(user_id)
            if business_profile:
                relevant_elements = get_relevant_business_elements(query, business_profile)

                if relevant_elements:
                    business_context = "Business Profile Context:\n"
                    for key, data in relevant_elements.items():
                        readable_key = key.replace("_", " ").title()
                        business_context += f"- {readable_key}: {data['value']}\n"
                    context_parts.append(business_context.strip())
                    logger.debug(
                        f"Added fallback business context with {len(relevant_elements)} elements"
                    )

        # Get conversational memory context using optimized Zep approach
        try:
            zep_memory.ensure_user_exists(user_id)
            memory = zep_memory.client.memory.get(session_id=session_id)

            if hasattr(memory, "context") and memory.context:
                conversational_context = (
                    f"Conversation Context:\n{memory.context[:800]}"  # Limit length
                )
                context_parts.append(conversational_context)
                logger.debug("Added conversational context from Zep memory.context")

        except Exception as memory_error:
            logger.debug(f"Zep memory context not available: {memory_error}")
            # Fallback to basic recent facts if memory.context fails
            try:
                user_memory = zep_memory.get_relevant_memory(session_id, query, limit=3)
                if user_memory and user_memory.get("facts"):
                    facts_context = "Recent Facts:\n" + "\n".join(
                        [f"- {fact}" for fact in user_memory["facts"][:3]]
                    )
                    context_parts.append(facts_context)
                    logger.debug("Used fallback facts context")
            except Exception:
                pass  # No conversational context available

    except Exception as e:
        logger.warning(f"Error getting optimized user context: {e}")

    # Combine all context parts
    if context_parts:
        combined_context = "\n\n".join(context_parts)
        # Ensure context doesn't exceed token limits (approximately 1000 tokens = 4000 chars)
        if len(combined_context) > 3500:
            combined_context = combined_context[:3500] + "..."
        return f"\n\nPersonalized Context:\n{combined_context}"

    return ""


def estimate_token_count(text: str) -> int:
    """Rough estimation of token count (approximately 4 characters per token)"""
    return len(text) // 4


def manage_context_length(
    expert_context: str, user_context: str, max_tokens: int = 2000
) -> tuple[str, str]:
    """
    Manage context length to fit within token limits with intelligent prioritization

    Args:
        expert_context: Expert knowledge graph context
        user_context: User's business profile and conversational context
        max_tokens: Maximum token budget for context

    Returns:
        Tuple of (managed_expert_context, managed_user_context)
    """
    expert_tokens = estimate_token_count(expert_context)
    user_tokens = estimate_token_count(user_context)
    total_tokens = expert_tokens + user_tokens

    if total_tokens <= max_tokens:
        return expert_context, user_context

    # Allocate token budget: 40% expert, 60% user (since user context is more personalized)
    expert_budget = int(max_tokens * 0.4)
    user_budget = int(max_tokens * 0.6)

    # Truncate expert context if needed
    managed_expert = expert_context
    if expert_tokens > expert_budget:
        # Keep the most important parts (first few entries)
        lines = expert_context.split("\n")
        truncated_lines = []
        current_tokens = 0

        for line in lines:
            line_tokens = estimate_token_count(line)
            if current_tokens + line_tokens > expert_budget:
                if len(truncated_lines) == 0:  # Always keep at least one line
                    truncated_lines.append(line[: expert_budget * 4] + "...")
                break
            truncated_lines.append(line)
            current_tokens += line_tokens

        managed_expert = "\n".join(truncated_lines)
        if len(truncated_lines) < len(lines):
            managed_expert += f"\n... ({len(lines) - len(truncated_lines)} more expert insights available)"

    # Truncate user context if needed (prioritize business profile over conversation)
    managed_user = user_context
    if user_tokens > user_budget:
        # Split user context into business profile and conversation parts
        parts = user_context.split("\n\n")
        business_part = ""
        conversation_part = ""

        for part in parts:
            if "Business Profile Context:" in part:
                business_part = part
            elif "Conversation Context:" in part:
                conversation_part = part

        # Prioritize business profile (70% of user budget)
        business_budget = int(user_budget * 0.7)
        conversation_budget = user_budget - business_budget

        managed_parts = []

        # Handle business profile
        if business_part:
            business_tokens = estimate_token_count(business_part)
            if business_tokens > business_budget:
                # Keep most relevant business elements
                lines = business_part.split("\n")
                truncated_business = []
                current_tokens = 0

                for line in lines:
                    line_tokens = estimate_token_count(line)
                    if current_tokens + line_tokens > business_budget:
                        break
                    truncated_business.append(line)
                    current_tokens += line_tokens

                managed_parts.append("\n".join(truncated_business))
            else:
                managed_parts.append(business_part)

        # Handle conversation context
        if conversation_part:
            conversation_tokens = estimate_token_count(conversation_part)
            if conversation_tokens > conversation_budget:
                # Keep the most recent/relevant parts
                truncated_conversation = (
                    conversation_part[: conversation_budget * 4] + "..."
                )
                managed_parts.append(truncated_conversation)
            else:
                managed_parts.append(conversation_part)

        managed_user = "\n\n".join(managed_parts)

    # Log context management statistics
    final_expert_tokens = estimate_token_count(managed_expert)
    final_user_tokens = estimate_token_count(managed_user)
    logger.debug(
        f"Context management: {expert_tokens}→{final_expert_tokens} expert, {user_tokens}→{final_user_tokens} user tokens"
    )

    return managed_expert, managed_user


app = FastAPI(
    title="Mental Model Knowledge Graph API",
    description="A Neo4j-based knowledge graph system for building and exploring mental models",
    version="1.0.0",
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
    # NEW: Zep integration fields
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class TokensUsed(BaseModel):
    input: Optional[int]
    output: Optional[int]


class ChatResponse(BaseModel):
    answer: str
    context: List[Dict]
    conversation_length: int
    tokens_used: TokensUsed


# Chat persistence models
class CreateSessionRequest(BaseModel):
    user_id: str
    title: Optional[str] = None


class AddMessageRequest(BaseModel):
    session_id: str
    role: str
    content: str
    metadata: Optional[Dict] = None


class UpdateSessionRequest(BaseModel):
    title: Optional[str] = None
    metadata: Optional[Dict] = None


class SessionResponse(BaseModel):
    id: str
    user_id: str
    title: Optional[str]
    created_at: str
    updated_at: str
    metadata: Dict


class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    timestamp: str
    metadata: Dict


def generate_query_embedding(text):
    # CORRECTED: Specify embedding_types and access the .float attribute.
    response = cohere_client.embed(
        texts=[text],
        model="embed-english-v3.0",
        input_type="search_query",
        embedding_types=["float"],
    )
    return response.embeddings.float[0]  # type: ignore


@app.post("/api/chat", response_model=ChatResponse)
async def chat(query: ChatQuery):
    try:
        # Generate embedding for the current question
        embedding = generate_query_embedding(query.question)

        # Retrieve relevant context from expert knowledge graph
        with get_db_session() as session:
            result = session.run(
                """
                CALL db.index.vector.queryNodes('entity_embeddings', 5, $embedding) YIELD node, score
                WHERE score > 0.5
                WITH node
                OPTIONAL MATCH (node)-[r]-(connected:Entity)
                RETURN node.id as entity, node.description as description,
                       collect(DISTINCT {
                           type: type(r),
                           connected: connected.id
                       }) as relationships
            """,
                {"embedding": embedding},
            )
            context_data = [dict(record) for record in result]

        # Build expert knowledge graph context string
        if context_data:
            expert_context_str = "Expert Knowledge Graph Context:\n" + "\n".join(
                [f"- {item['entity']}: {item['description']}" for item in context_data]
            )
        else:
            expert_context_str = (
                "No specific expert knowledge graph context found for this question."
            )

        # Get optimized user context from Zep (business profile + conversational memory)
        user_context_str = ""
        if query.session_id and query.user_id:
            user_context_str = await get_optimized_user_context(
                user_id=query.user_id, session_id=query.session_id, query=query.question
            )

        # Apply intelligent context length management
        managed_expert_context, managed_user_context = manage_context_length(
            expert_context_str, user_context_str, max_tokens=2000
        )

        # Combine managed contexts
        context_str = managed_expert_context + managed_user_context

        # Build conversation messages with rolling window (last 15 messages)
        messages = []

        # Add conversation history (limit to last 15 messages)
        recent_history = query.conversation_history[-15:]

        for msg in recent_history:
            messages.append({"role": msg.role, "content": msg.content})

        # Add chat context node ONLY if explicitly provided (user clicked "Chat with this node")
        chat_context_str = ""
        if query.chat_context_node:
            chat_context_str = f"\n\nChat Context Node (User explicitly added this for focused discussion):\n- Name: {query.chat_context_node.name}\n- Type: {query.chat_context_node.type}\n- Description: {query.chat_context_node.description}\n- Theme: {query.chat_context_node.theme}\n- Labels: {', '.join(query.chat_context_node.labels) if query.chat_context_node.labels else 'None'}"
            logger.info(f"Chat context node added: {query.chat_context_node.name}")
        else:
            logger.info(
                "No chat context node provided - proceeding with general knowledge graph context only"
            )

        # Add current question with knowledge graph context and optional chat context node
        current_message = (
            f"{context_str}{chat_context_str}\n\nQuestion: {query.question}"
        )
        messages.append({"role": "user", "content": current_message})

        # Call Claude with conversation history and prompt caching
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,  # Increased for large context windows and extended responses
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {
                        "type": "ephemeral"
                    },  # Cache the long system prompt
                }
            ],
            messages=messages,
            stream=False,  # We'll implement streaming in a separate endpoint
        )

        answer_text = ""
        for block in response.content:
            if block.type == "text":
                answer_text = block.text
                break

        return {
            "answer": answer_text,
            "context": context_data,
            "conversation_length": len(recent_history) + 1,  # Include current message
            "tokens_used": {
                "input": (
                    response.usage.input_tokens if hasattr(response, "usage") else None
                ),
                "output": (
                    response.usage.output_tokens if hasattr(response, "usage") else None
                ),
            },
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
            result = session.run(
                """
                CALL db.index.vector.queryNodes('entity_embeddings', 5, $embedding) YIELD node, score
                WHERE score > 0.5
                WITH node
                OPTIONAL MATCH (node)-[r]-(connected:Entity)
                RETURN node.id as entity, node.description as description,
                       collect(DISTINCT {
                           type: type(r),
                           connected: connected.id
                       }) as relationships
            """,
                {"embedding": embedding},
            )
            context_data = [dict(record) for record in result]

        # Build expert knowledge graph context string
        if context_data:
            expert_context_str = "Expert Knowledge Graph Context:\n" + "\n".join(
                [f"- {item['entity']}: {item['description']}" for item in context_data]
            )
        else:
            expert_context_str = (
                "No specific expert knowledge graph context found for this question."
            )

        # Get optimized user context from Zep (business profile + conversational memory)
        user_context_str = ""
        if query.session_id and query.user_id:
            user_context_str = await get_optimized_user_context(
                user_id=query.user_id, session_id=query.session_id, query=query.question
            )

        # Apply intelligent context length management for streaming
        managed_expert_context, managed_user_context = manage_context_length(
            expert_context_str, user_context_str, max_tokens=2000
        )

        # Combine managed contexts
        context_str = managed_expert_context + managed_user_context

        # Build conversation messages with rolling window (last 15 messages)
        messages = []

        # Add conversation history (limit to last 15 messages)
        recent_history = query.conversation_history[-15:]

        for msg in recent_history:
            messages.append({"role": msg.role, "content": msg.content})

        # Add chat context node ONLY if explicitly provided
        chat_context_str = ""
        if query.chat_context_node:
            chat_context_str = f"\n\nChat Context Node (User explicitly added this for focused discussion):\n- Name: {query.chat_context_node.name}\n- Type: {query.chat_context_node.type}\n- Description: {query.chat_context_node.description}\n- Theme: {query.chat_context_node.theme}\n- Labels: {', '.join(query.chat_context_node.labels) if query.chat_context_node.labels else 'None'}"
            logger.info(
                f"Streaming chat context node added: {query.chat_context_node.name}"
            )
        else:
            logger.info("Streaming: No chat context node provided")

        # Add current question with knowledge graph context and optional chat context node
        current_message = (
            f"{context_str}{chat_context_str}\n\nQuestion: {query.question}"
        )
        messages.append({"role": "user", "content": current_message})

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
                            "cache_control": {"type": "ephemeral"},
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
            },
        )

    except Exception as e:
        logger.error(f"Error in /api/chat/stream: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred during streaming."
        )


@app.get("/api/graph")
async def get_graph():
    # Check cache first
    current_time = time.time()
    if (
        _graph_cache["data"] is not None
        and current_time - _graph_cache["timestamp"] < CACHE_TTL
    ):
        logger.info("Returning cached graph data")
        return JSONResponse(
            content=_graph_cache["data"],
            headers={"Cache-Control": "public, max-age=300"},
        )

    logger.info("Cache miss - fetching fresh graph data")
    with get_db_session() as session:
        # Get ALL nodes - both Entity nodes and standalone nodes (optimized)
        nodes_result = session.run(
            """
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
        """
        )

        # Get ALL relationships separately - optimized with constraints
        edges_result = session.run(
            """
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
        """
        )

        nodes, edges = [], []
        seen_nodes = set()

        # Process nodes
        for record in nodes_result:
            if record["id"] not in seen_nodes:
                nodes.append(
                    {
                        "id": record["id"],
                        "label": record["id"],  # Use ID as label
                        "type": record["type"],
                        "description": record["description"] or "",
                        "content": record["content"] or "",
                        "theme": record["theme"] or "",
                    }
                )
                seen_nodes.add(record["id"])

        # Process edges - no restrictions, include all relationships
        edge_set = set()  # To avoid duplicates
        for record in edges_result:
            from_node, to_node, rel_type, is_outgoing = (
                record["from_node"],
                record["to_node"],
                record["rel_type"],
                record["is_outgoing"],
            )
            if (
                from_node
                and to_node
                and from_node in seen_nodes
                and to_node in seen_nodes
            ):
                # Use the actual direction from the database
                if is_outgoing:
                    # a->b: from_node is correct
                    actual_from, actual_to = from_node, to_node
                else:
                    # b->a: swap direction
                    actual_from, actual_to = to_node, from_node

                edge_key = (actual_from, actual_to, rel_type)
                if edge_key not in edge_set:
                    edges.append(
                        {"from": actual_from, "to": actual_to, "label": rel_type}
                    )
                    edge_set.add(edge_key)

        # Cache the result
        graph_data = {"nodes": nodes, "edges": edges}
        _graph_cache["data"] = graph_data
        _graph_cache["timestamp"] = current_time
        logger.info(f"Cached graph data: {len(nodes)} nodes, {len(edges)} edges")

        return JSONResponse(
            content=graph_data, headers={"Cache-Control": "public, max-age=300"}
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


@app.get("/api/graph/subgraph/{node_id}")
async def get_node_subgraph(node_id: str, include_connections: bool = True):
    """
    Get a subgraph focused on a specific node, optionally including connected nodes.

    Args:
        node_id: The ID of the target node
        include_connections: Whether to include directly connected nodes
    """
    try:
        with get_db_session() as session:
            if include_connections:
                # Simpler approach - get nodes and relationships in one query
                query = """
                    MATCH (target)
                    WHERE (target:Entity OR target:Theme OR target:Pattern OR target:Example OR target:Principle OR target:Expert OR target:MentalModel)
                    AND (
                        (target:Theme AND target.name = $node_id) OR
                        (target.id = $node_id) OR 
                        (target.name = $node_id)
                    )
                    
                    OPTIONAL MATCH (target)-[r]-(connected)
                    WHERE connected:Entity OR connected:Theme OR connected:Pattern OR connected:Example OR connected:Principle OR connected:Expert OR connected:MentalModel
                    
                    RETURN 
                        target,
                        collect(DISTINCT connected) as connected_nodes,
                        collect(DISTINCT r) as relationships
                """
            else:
                # Get only the target node - no relationships
                query = """
                    MATCH (target)
                    WHERE (target:Entity OR target:Theme OR target:Pattern OR target:Example OR target:Principle OR target:Expert OR target:MentalModel)
                    AND (
                        (target:Theme AND target.name = $node_id) OR
                        (target.id = $node_id) OR 
                        (target.name = $node_id)
                    )
                    
                    RETURN 
                        target,
                        [] as connected_nodes,
                        [] as relationships
                """

            result = session.run(query, {"node_id": node_id})

            nodes = []
            edges = []
            seen_nodes = set()
            edge_set = set()

            def get_node_id(node):
                if node is None:
                    return None
                if "Theme" in node.labels and node.get("name"):
                    return node["name"]
                elif node.get("id"):
                    return node["id"]
                elif node.get("name"):
                    return node["name"]
                else:
                    return str(node.id)

            def get_node_type(node):
                if node is None:
                    return "Entity"
                if "Theme" in node.labels:
                    return "Theme"
                elif "Entity" in node.labels and node.get("category"):
                    return node["category"]
                elif "Pattern" in node.labels:
                    return "Pattern"
                elif "Example" in node.labels:
                    return "Example"
                elif "Principle" in node.labels:
                    return "Principle"
                elif "Expert" in node.labels:
                    return "Expert"
                elif "MentalModel" in node.labels:
                    return "MentalModel"
                else:
                    return "Entity"

            for record in result:
                target_node = record["target"]
                connected_nodes = record.get("connected_nodes", [])
                relationships = record.get("relationships", [])

                # Add target node
                target_id = get_node_id(target_node)
                if target_id and target_id not in seen_nodes:
                    nodes.append(
                        {
                            "id": target_id,
                            "label": target_id,
                            "type": get_node_type(target_node),
                            "description": target_node.get("description", ""),
                            "content": target_node.get("content", ""),
                            "theme": target_node.get("theme", ""),
                        }
                    )
                    seen_nodes.add(target_id)

                if include_connections:
                    # Add connected nodes
                    for connected_node in connected_nodes:
                        if connected_node is not None:
                            connected_id = get_node_id(connected_node)
                            if connected_id and connected_id not in seen_nodes:
                                nodes.append(
                                    {
                                        "id": connected_id,
                                        "label": connected_id,
                                        "type": get_node_type(connected_node),
                                        "description": connected_node.get(
                                            "description", ""
                                        ),
                                        "content": connected_node.get("content", ""),
                                        "theme": connected_node.get("theme", ""),
                                    }
                                )
                                seen_nodes.add(connected_id)

                    # Add relationships
                    for rel in relationships:
                        if rel is not None:
                            start_node = rel.start_node
                            end_node = rel.end_node
                            rel_type = rel.type

                            start_id = get_node_id(start_node)
                            end_id = get_node_id(end_node)

                            if (
                                start_id
                                and end_id
                                and start_id in seen_nodes
                                and end_id in seen_nodes
                            ):
                                edge_key = (start_id, end_id, rel_type)
                                if edge_key not in edge_set:
                                    edges.append(
                                        {
                                            "from": start_id,
                                            "to": end_id,
                                            "label": rel_type,
                                        }
                                    )
                                    edge_set.add(edge_key)

            if not nodes:
                raise HTTPException(
                    status_code=404, detail=f"Node '{node_id}' not found"
                )

            subgraph_data = {"nodes": nodes, "edges": edges}
            logger.info(
                f"Subgraph for '{node_id}': {len(nodes)} nodes, {len(edges)} edges, include_connections={include_connections}"
            )

            return JSONResponse(content=subgraph_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /api/graph/subgraph: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve subgraph")


@app.get("/api/search", response_model=SearchResponse)
async def search_nodes(
    q: str, limit: int = 10, threshold: float = 0.3, include_themes: bool = False
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
            raise HTTPException(
                status_code=400, detail="Query must be at least 2 characters long"
            )

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
            result = session.run(
                search_query,
                {"embedding": embedding, "limit": limit, "threshold": threshold},
            )

            search_results = []
            for record in result:
                search_results.append(
                    SearchResult(
                        id=record["id"],
                        type=record["type"],
                        description=record["description"] or "",
                        theme=record.get("theme"),
                        score=record["score"],
                    )
                )

        execution_time = int((time.time() - start_time) * 1000)

        logger.info(
            f"Search query '{q}' returned {len(search_results)} results in {execution_time}ms"
        )

        return SearchResponse(
            results=search_results,
            query=q.strip(),
            total_count=len(search_results),
            execution_time_ms=execution_time,
        )

    except Exception as e:
        logger.error(f"Error in /api/search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Search request failed")


# Chat Persistence Endpoints
@app.post("/api/chat/sessions", response_model=SessionResponse)
async def create_chat_session(request: CreateSessionRequest):
    """Create a new chat session for a user"""
    try:
        session_data = await supabase_service.create_chat_session(
            user_id=request.user_id, title=request.title
        )
        if not session_data:
            raise HTTPException(status_code=500, detail="Failed to create session")

        return SessionResponse(
            id=session_data["id"],
            user_id=session_data["user_id"],
            title=session_data.get("title"),
            created_at=session_data["created_at"],
            updated_at=session_data["updated_at"],
            metadata=session_data.get("metadata", {}),
        )
    except Exception as e:
        logger.error(f"Error creating chat session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create chat session")


@app.get("/api/chat/sessions/{user_id}")
async def get_user_sessions(user_id: str, limit: int = 50, offset: int = 0):
    """Get all chat sessions for a user"""
    try:
        sessions = await supabase_service.get_user_sessions(user_id, limit, offset)
        return {
            "sessions": [
                SessionResponse(
                    id=s["id"],
                    user_id=s["user_id"],
                    title=s.get("title"),
                    created_at=s["created_at"],
                    updated_at=s["updated_at"],
                    metadata=s.get("metadata", {}),
                )
                for s in sessions
            ],
            "total": len(sessions),
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"Error getting user sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user sessions")


@app.get("/api/chat/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, limit: int = 100):
    """Get all messages for a chat session"""
    try:
        messages = await supabase_service.get_session_messages(session_id, limit)
        return {
            "messages": [
                MessageResponse(
                    id=m["id"],
                    session_id=m["session_id"],
                    role=m["role"],
                    content=m["content"],
                    timestamp=m["timestamp"],
                    metadata=m.get("metadata", {}),
                )
                for m in messages
            ],
            "total": len(messages),
            "session_id": session_id,
        }
    except Exception as e:
        logger.error(f"Error getting session messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to get session messages")


@app.post("/api/chat/messages", response_model=MessageResponse)
async def add_message(request: AddMessageRequest):
    """Add a message to a chat session"""
    try:
        message_data = await supabase_service.add_message(
            session_id=request.session_id,
            role=request.role,
            content=request.content,
            metadata=request.metadata,
        )
        if not message_data:
            raise HTTPException(status_code=500, detail="Failed to add message")

        # Add message to Zep for knowledge extraction
        try:
            # Get session to determine user_id
            session_data = await supabase_service.get_session(request.session_id)
            if session_data and session_data.get("user_id"):
                user_id = session_data["user_id"]

                # Add this message to Zep memory
                zep_memory.add_conversation_memory(
                    user_id=user_id,
                    session_id=request.session_id,
                    messages=[{"role": request.role, "content": request.content}],
                )
                logger.info(
                    f"Added message to Zep memory for user {user_id}, session {request.session_id}"
                )
        except Exception as zep_error:
            logger.warning(f"Failed to add message to Zep memory: {zep_error}")
            # Continue without failing the message addition

        # Auto-generate title if this is an assistant message and session doesn't have a title
        if request.role == "assistant":
            try:
                # Get session data to check if it already has a title
                session_data = await supabase_service.get_session(request.session_id)

                # Only generate title if session exists and doesn't have a meaningful title
                if session_data and (
                    not session_data.get("title")
                    or session_data.get("title") == "Untitled conversation"
                ):
                    # Check if we have enough messages for title generation
                    messages = await supabase_service.get_session_messages(
                        request.session_id, limit=10
                    )

                    if len(messages) >= 2:  # Need at least user + assistant message
                        try:
                            title = await generate_session_title(request.session_id)
                            if title:
                                await supabase_service.update_session(
                                    request.session_id, {"title": title}
                                )
                                logger.info(
                                    f"Auto-generated title for session {request.session_id}: {title}"
                                )
                        except Exception as title_error:
                            logger.warning(
                                f"Failed to auto-generate title for session {request.session_id}: {title_error}"
                            )
                            # Continue without failing the message addition
            except Exception as auto_title_error:
                logger.warning(
                    f"Auto-title generation failed for session {request.session_id}: {auto_title_error}"
                )
                # Continue without failing the message addition

        return MessageResponse(
            id=message_data["id"],
            session_id=message_data["session_id"],
            role=message_data["role"],
            content=message_data["content"],
            timestamp=message_data["timestamp"],
            metadata=message_data.get("metadata", {}),
        )
    except Exception as e:
        logger.error(f"Error adding message: {e}")
        raise HTTPException(status_code=500, detail="Failed to add message")


@app.put("/api/chat/sessions/{session_id}")
async def update_session(session_id: str, request: UpdateSessionRequest):
    """Update a chat session"""
    try:
        updates = {}
        if request.title is not None:
            updates["title"] = request.title
        if request.metadata is not None:
            updates["metadata"] = request.metadata

        if not updates:
            raise HTTPException(status_code=400, detail="No valid updates provided")

        session_data = await supabase_service.update_session(session_id, updates)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")

        return SessionResponse(
            id=session_data["id"],
            user_id=session_data["user_id"],
            title=session_data.get("title"),
            created_at=session_data["created_at"],
            updated_at=session_data["updated_at"],
            metadata=session_data.get("metadata", {}),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session: {e}")
        raise HTTPException(status_code=500, detail="Failed to update session")


@app.delete("/api/chat/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session and all its messages"""
    try:
        await supabase_service.delete_session(session_id)
        return {"message": "Session deleted successfully", "session_id": session_id}
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete session")


async def generate_session_title(session_id: str) -> str:
    """Generate a title for a session based on initial messages."""
    try:
        # Get the first few messages from the session
        messages = await supabase_service.get_session_messages(session_id, limit=4)

        if not messages or len(messages) < 2:
            return None  # Not enough messages to generate a title

        # Find the first user message and assistant response
        user_message = None
        assistant_message = None

        for msg in messages:
            if msg["role"] == "user" and user_message is None:
                user_message = msg["content"]
            elif (
                msg["role"] == "assistant"
                and assistant_message is None
                and user_message is not None
            ):
                assistant_message = msg["content"]
                break

        if not user_message:
            return None

        # Create a prompt for title generation
        title_prompt = f"""Generate a concise, descriptive title (maximum 6 words) for this conversation based on the initial exchange:

User: {user_message[:300]}...
{f'Assistant: {assistant_message[:200]}...' if assistant_message else ''}

Return only the title, no additional text or punctuation. Make it specific to the topic discussed.

Title:"""

        # Use Anthropic to generate the title
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=20,
            temperature=0.3,  # Lower temperature for more consistent titles
            messages=[{"role": "user", "content": title_prompt}],
        )

        title = ""
        for block in response.content:
            if block.type == "text":
                title = block.text.strip()
                break

        # Clean up the title (remove quotes, ensure reasonable length)
        title = title.strip("\"'").strip()
        if len(title) > 50:
            title = title[:47] + "..."

        return title if title else None

    except Exception as e:
        logger.error(f"Error generating session title: {e}")
        return None


@app.post("/api/chat/sessions/{session_id}/generate-title")
async def generate_title_endpoint(session_id: str):
    """Generate and update session title based on conversation content"""
    try:
        # Generate the title
        title = await generate_session_title(session_id)

        if not title:
            raise HTTPException(
                status_code=400,
                detail="Unable to generate title - session may not have enough messages",
            )

        # Update the session with the new title
        session_data = await supabase_service.update_session(
            session_id, {"title": title}
        )

        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")

        return {
            "session_id": session_id,
            "title": title,
            "message": "Title generated successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in generate title endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate session title")


@app.get("/api/chat/search")
async def search_messages(user_id: str, q: str, limit: int = 20):
    """Search messages across all user sessions"""
    try:
        if not q or len(q.strip()) < 2:
            raise HTTPException(
                status_code=400, detail="Query must be at least 2 characters long"
            )

        results = await supabase_service.search_messages(user_id, q.strip(), limit)
        return {
            "results": results,
            "query": q.strip(),
            "user_id": user_id,
            "total": len(results),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to search messages")


# Business Profile Questionnaire Endpoints
class BusinessProfileAnswer(BaseModel):
    user_id: str
    question_id: int
    answer: str
    answered_at: Optional[str] = None
    session_id: Optional[str] = None


class BusinessProfileProgressResponse(BaseModel):
    user_id: str
    questions_completed: int
    total_questions: int
    started_at: Optional[str]
    completed_at: Optional[str]
    last_question_at: Optional[str]
    current_question_id: Optional[int]


class BusinessProfileQuestionResponse(BaseModel):
    id: int
    question_text: str
    answer_type: str
    options: Optional[Union[List[str], Dict[str, Any]]]
    order_index: int


@app.get("/api/business-profile/questions")
async def get_business_profile_questions():
    """Get all business profile questions"""
    try:
        questions = await supabase_service.get_business_profile_questions()
        return {
            "questions": [
                BusinessProfileQuestionResponse(
                    id=q["id"],
                    question_text=q["question_text"],
                    answer_type=q["answer_type"],
                    options=q.get("options"),
                    order_index=q["order_index"],
                )
                for q in questions
            ],
            "total": len(questions),
        }
    except Exception as e:
        logger.error(f"Error getting business profile questions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get questions")


@app.get("/api/business-profile/progress/{user_id}")
async def get_business_profile_progress(user_id: str):
    """Get user's business profile progress and existing answers"""
    try:
        progress = await supabase_service.get_business_profile_progress(user_id)
        answers = await supabase_service.get_business_profile_answers(user_id)

        return {
            "progress": (
                BusinessProfileProgressResponse(
                    user_id=progress["user_id"],
                    questions_completed=progress["questions_completed"],
                    total_questions=progress["total_questions"],
                    started_at=progress.get("started_at"),
                    completed_at=progress.get("completed_at"),
                    last_question_at=progress.get("last_question_at"),
                    current_question_id=progress.get("current_question_id"),
                )
                if progress
                else None
            ),
            "answers": answers or [],
        }
    except Exception as e:
        logger.error(f"Error getting business profile progress: {e}")
        raise HTTPException(status_code=500, detail="Failed to get progress")


@app.post("/api/business-profile/answer")
async def save_business_profile_answer(request: BusinessProfileAnswer):
    """Save a business profile answer and update progress"""
    try:
        # Save the answer
        answer_data = await supabase_service.save_business_profile_answer(
            user_id=request.user_id,
            question_id=request.question_id,
            answer=request.answer,
            answered_at=request.answered_at,
            session_id=request.session_id,
        )

        if not answer_data:
            raise HTTPException(status_code=500, detail="Failed to save answer")

        # Get updated progress
        progress = await supabase_service.get_business_profile_progress(request.user_id)

        # Sync to Zep if profile is getting close to completion or completed
        if (
            progress and progress["questions_completed"] >= 8
        ):  # Sync when 8+ questions answered
            try:
                # Get all answers to create comprehensive business profile for Zep
                all_answers = await supabase_service.get_business_profile_answers(
                    request.user_id
                )

                if all_answers:
                    # Create structured business profile data for Zep
                    business_profile = {}
                    question_map = {
                        1: "biggest_challenge",
                        2: "employee_count",
                        3: "revenue_range",
                        4: "industry",
                        5: "success_metrics",
                        6: "work_similarity_to_team",
                        7: "main_business_goal",
                        8: "business_operations_when_away",
                        9: "critical_decisions_only_owner",
                        10: "team_capacity_for_growth",
                        11: "profitability_confidence",
                    }

                    for answer in all_answers:
                        key = question_map.get(answer["question_id"])
                        if key:
                            business_profile[key] = answer["answer"]

                    # Add to Zep knowledge graph
                    zep_memory.add_business_data(
                        user_id=request.user_id,
                        data={"business_profile": business_profile},
                        data_type="json",
                    )

                    # Mark answers as synced to Zep
                    await supabase_service.mark_answers_synced_to_zep(request.user_id)

                    logger.info(
                        f"Synced business profile to Zep for user {request.user_id}"
                    )

            except Exception as zep_error:
                logger.warning(f"Failed to sync business profile to Zep: {zep_error}")
                # Continue without failing the answer save

        return {
            "answer": answer_data,
            "progress": (
                BusinessProfileProgressResponse(
                    user_id=progress["user_id"],
                    questions_completed=progress["questions_completed"],
                    total_questions=progress["total_questions"],
                    started_at=progress.get("started_at"),
                    completed_at=progress.get("completed_at"),
                    last_question_at=progress.get("last_question_at"),
                    current_question_id=progress.get("current_question_id"),
                )
                if progress
                else None
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving business profile answer: {e}")
        raise HTTPException(status_code=500, detail="Failed to save answer")


@app.get("/api/business-profile/nudge-status/{user_id}")
async def get_nudge_status(user_id: str):
    """Get nudging status and determine what type of nudge to show"""
    try:
        progress = await supabase_service.get_business_profile_progress(user_id)

        if not progress:
            # User hasn't started
            return {
                "user_type": "not_started",
                "should_show_nudge": True,
                "progress": None,
            }
        elif progress["completed_at"]:
            # User completed
            return {
                "user_type": "completed",
                "should_show_nudge": False,
                "progress": progress,
            }
        else:
            # User started but not finished
            return {
                "user_type": "in_progress",
                "should_show_nudge": True,
                "progress": progress,
            }

    except Exception as e:
        logger.error(f"Error getting nudge status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get nudge status")


@app.post("/api/business-profile/nudge-dismissed")
async def record_nudge_dismissed(user_id: str = None):
    """Record that user dismissed a nudge (for analytics/frequency control)"""
    try:
        if user_id:
            await supabase_service.record_nudge_dismissed(user_id)
        return {"message": "Nudge dismissal recorded"}
    except Exception as e:
        logger.error(f"Error recording nudge dismissal: {e}")
        # Don't fail the request for this
        return {"message": "Nudge dismissal recording failed"}


# Zep Knowledge Graph Endpoints
class BusinessDataRequest(BaseModel):
    user_id: str
    data: Dict[str, Any]
    data_type: str = "json"


@app.post("/api/user/business-data")
async def add_business_data(request: BusinessDataRequest):
    """Add structured business data to user's knowledge graph"""
    try:
        zep_memory.add_business_data(
            user_id=request.user_id, data=request.data, data_type=request.data_type
        )
        return {
            "message": "Business data added successfully",
            "user_id": request.user_id,
            "data_type": request.data_type,
        }
    except Exception as e:
        logger.error(f"Error adding business data: {e}")
        raise HTTPException(status_code=500, detail="Failed to add business data")


@app.get("/api/user/{user_id}/knowledge-graph")
async def get_user_knowledge_graph(user_id: str):
    """Get user's personal knowledge graph for visualization"""
    try:
        knowledge_graph = zep_memory.get_user_knowledge_graph(user_id)
        return knowledge_graph
    except Exception as e:
        logger.error(f"Error retrieving user knowledge graph: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve knowledge graph"
        )


@app.get("/api/user/{user_id}/memory/{session_id}")
async def get_session_memory(
    user_id: str, session_id: str, query: Optional[str] = None
):
    """Get relevant memory context for a session"""
    try:
        memory_context = zep_memory.get_relevant_memory(
            session_id=session_id, query=query, limit=10
        )
        return {
            "user_id": user_id,
            "session_id": session_id,
            "memory_context": memory_context,
            "query": query,
        }
    except Exception as e:
        logger.error(f"Error retrieving session memory: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve session memory")


@app.delete("/api/user/{user_id}/data")
async def delete_user_data(user_id: str):
    """Delete all user data from Zep (for privacy compliance)"""
    try:
        success = zep_memory.delete_user_data(user_id)
        if success:
            return {"message": "User data deleted successfully", "user_id": user_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete user data")
    except Exception as e:
        logger.error(f"Error deleting user data: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete user data")


# ===== CHAT-INTEGRATED QUESTIONNAIRE ENDPOINTS =====

class QuestionnaireStartRequest(BaseModel):
    user_id: str

class QuestionnaireAnswerRequest(BaseModel):
    user_id: str
    question_id: int
    answer_text: str

class QuestionnaireCommandRequest(BaseModel):
    user_id: str
    command: str

class QuestionnaireEditRequest(BaseModel):
    user_id: str
    question_id: int
    new_answer: str


# Import questionnaire service
from questionnaire_service import questionnaire_service

@app.post("/api/questionnaire/start")
async def start_questionnaire(request: QuestionnaireStartRequest):
    """Initialize questionnaire session for user"""
    try:
        result = await questionnaire_service.start_questionnaire(request.user_id)
        return result
    except Exception as e:
        logger.error(f"Error starting questionnaire: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/questionnaire/current/{user_id}")
async def get_current_question(user_id: str):
    """Get current question and progress for user"""
    try:
        result = await questionnaire_service.get_current_question(user_id)
        if result is None:
            return {"status": "not_started", "message": "No active questionnaire found"}
        return result
    except Exception as e:
        logger.error(f"Error getting current question: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/questionnaire/answer")
async def submit_answer(request: QuestionnaireAnswerRequest):
    """Submit answer for a question, save to DB and Zep, return next question"""
    try:
        logger.info(f"🔍 Received questionnaire answer: user_id={request.user_id[:8]}..., question_id={request.question_id}, answer_text='{request.answer_text[:50]}...'")
        
        result = await questionnaire_service.submit_answer(
            request.user_id, 
            request.question_id, 
            request.answer_text
        )
        
        logger.info(f"✅ Questionnaire answer result: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ Error submitting answer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/questionnaire/command")
async def handle_command(request: QuestionnaireCommandRequest):
    """Handle special commands: skip, pause, previous, resume"""
    try:
        result = await questionnaire_service.handle_command(
            request.user_id, 
            request.command
        )
        return result
    except Exception as e:
        logger.error(f"Error handling command: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/questionnaire/all-responses/{user_id}")
async def get_all_responses(user_id: str):
    """Get all user responses for edit form"""
    try:
        responses = await questionnaire_service.get_all_responses(user_id)
        return {"responses": responses}
    except Exception as e:
        logger.error(f"Error getting all responses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/questionnaire/edit")
async def edit_response(request: QuestionnaireEditRequest):
    """Update a specific question response and sync to Zep"""
    try:
        success = await questionnaire_service.update_response(
            request.user_id,
            request.question_id,
            request.new_answer
        )
        if success:
            return {"message": "Response updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update response")
    except Exception as e:
        logger.error(f"Error editing response: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/questionnaire/status/{user_id}")
async def get_questionnaire_status(user_id: str):
    """Get comprehensive questionnaire status for user"""
    try:
        status = await questionnaire_service.get_questionnaire_status(user_id)
        return status
    except Exception as e:
        logger.error(f"Error getting questionnaire status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
