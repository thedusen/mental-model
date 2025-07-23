"""
Zep Memory Management Module
Handles user knowledge graph extraction and GraphRAG integration
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from zep_cloud.client import Zep
from zep_cloud import Message, User
from config import zep_client

logger = logging.getLogger(__name__)


class ZepMemoryManager:
    """Manages user memory and knowledge graphs using Zep"""

    def __init__(self):
        self.client = zep_client

    def ensure_user_exists(
        self, user_id: str, user_metadata: Optional[Dict[str, Any]] = None
    ) -> User:
        """
        Ensure a user exists in Zep, create if not exists

        Args:
            user_id: Unique user identifier (from Supabase)
            user_metadata: Optional metadata about the user (should include 'name' for display)

        Returns:
            User object from Zep
        """
        try:
            # Try to get existing user
            user = self.client.user.get(user_id)
            logger.info(f"Found existing Zep user: {user_id}")
            return user
        except Exception:
            # User doesn't exist, create new one
            logger.info(f"Creating new Zep user: {user_id}")

            # Ensure we have proper user metadata with display name
            default_metadata = {
                "name": user_id,  # Use user_id as fallback display name
                "created_at": str(datetime.now()),
                "user_type": "business_owner",
            }

            # Merge with provided metadata, giving priority to provided values
            final_metadata = {**default_metadata, **(user_metadata or {})}

            user = self.client.user.add(user_id=user_id, metadata=final_metadata)
            return user

    def add_conversation_memory(
        self, user_id: str, session_id: str, messages: List[Dict[str, str]]
    ) -> None:
        """
        Add conversation messages to Zep for automatic knowledge extraction

        Args:
            user_id: User identifier
            session_id: Session/conversation identifier
            messages: List of message dictionaries with 'role' and 'content'
        """
        try:
            # Ensure user exists
            self.ensure_user_exists(user_id)

            # Convert messages to Zep format
            zep_messages = []
            for msg in messages:
                zep_message = Message(
                    role=msg.get("role", "user"), content=msg.get("content", "")
                )
                zep_messages.append(zep_message)

            # Add messages to Zep memory
            self.client.memory.add(session_id=session_id, messages=zep_messages)

            logger.info(
                f"Added {len(zep_messages)} messages to Zep memory for session {session_id}"
            )

        except Exception as e:
            logger.error(f"Error adding conversation memory to Zep: {str(e)}")
            raise

    def add_business_data(
        self, user_id: str, data: Dict[str, Any], data_type: str = "json"
    ) -> None:
        """
        Add structured business data to user's knowledge graph with proper node creation

        Args:
            user_id: User identifier
            data: Business data to store (company info, projects, etc.)
            data_type: Type of data being stored
        """
        try:
            # Ensure user exists with proper metadata
            user_metadata = {
                "name": data.get("company_name", user_id),
                "business_type": data.get("business_type", "startup"),
                "industry": data.get("industry", "technology"),
            }
            self.ensure_user_exists(user_id, user_metadata)

            # Add structured data to Zep's graph for knowledge extraction
            import json

            # Zep expects standard types like "json", "text", etc.
            zep_data_type = (
                "json"
                if data_type in ["business_assessment", "user_profile"]
                else data_type
            )
            self.client.graph.add(
                user_id=user_id, data=json.dumps(data), type=zep_data_type
            )

            # Also add as conversation context for better integration
            data_summary = self._create_business_data_summary(data, data_type)
            business_message = Message(
                role="system", content=f"Business Assessment Data: {data_summary}"
            )

            # Create a special session for business data
            business_session_id = f"business_data_{user_id}"
            self.client.memory.add(
                session_id=business_session_id, messages=[business_message]
            )

            logger.info(f"Added business data to Zep for user {user_id}: {data_type}")

        except Exception as e:
            logger.error(f"Error adding business data to Zep: {str(e)}")
            raise

    def _create_business_data_summary(
        self, data: Dict[str, Any], data_type: str
    ) -> str:
        """Create a human-readable summary of business data for better node creation"""
        if data_type == "business_assessment":
            company = data.get("company_name", "Unknown Company")
            industry = data.get("industry", "Unknown Industry")
            stage = data.get("business_stage", "Unknown Stage")
            challenges = data.get("current_challenges", [])

            summary = f"{company} is a {stage} company in the {industry} industry."
            if challenges:
                summary += f" Current challenges include: {', '.join(challenges[:3])}."

            return summary
        else:
            # Generic summary for other data types
            return f"Business data of type {data_type}: {str(data)[:200]}..."

    def get_relevant_memory(
        self, session_id: str, query: Optional[str] = None, limit: int = 10
    ) -> Dict[str, Any]:
        """
        Retrieve relevant memory context for GraphRAG using optimized Zep API

        Args:
            session_id: Session identifier
            query: Optional query to search for relevant context (largely ignored in favor of context)
            limit: Maximum number of memories to return (for legacy compatibility)

        Returns:
            Dictionary containing relevant context optimized for LLM consumption
        """
        try:
            # Use the optimized memory.context approach recommended by Zep
            memory = self.client.memory.get(session_id=session_id)

            if hasattr(memory, "context") and memory.context:
                # The context field is an opinionated string containing facts and entities
                # relevant to the current conversation - this is the optimal approach
                return {
                    "context": memory.context,
                    "facts": self._extract_facts_from_context(memory.context),
                    "session_id": session_id,
                    "has_memory": True,
                }
            else:
                # Fallback to basic facts extraction if context isn't available
                facts = []
                if hasattr(memory, "facts") and memory.facts:
                    facts = [str(fact) for fact in memory.facts[:limit]]
                elif hasattr(memory, "messages") and memory.messages:
                    # Extract key information from recent messages as fallback
                    recent_messages = (
                        memory.messages[-3:]
                        if len(memory.messages) > 3
                        else memory.messages
                    )
                    facts = [
                        (
                            msg.content[:200] + "..."
                            if len(msg.content) > 200
                            else msg.content
                        )
                        for msg in recent_messages
                        if hasattr(msg, "content")
                    ]

                return {
                    "context": None,
                    "facts": facts,
                    "session_id": session_id,
                    "has_memory": len(facts) > 0,
                }

        except Exception as e:
            logger.error(f"Error retrieving memory from Zep: {str(e)}")
            # Return graceful fallback for error cases
            return {
                "context": None,
                "facts": [],
                "session_id": session_id,
                "has_memory": False,
                "error": str(e),
            }

    def _extract_facts_from_context(self, context: str) -> List[str]:
        """Extract individual facts from Zep's context string for legacy compatibility"""
        if not context:
            return []

        facts = []
        # Look for facts section in context
        if "<FACTS>" in context and "</FACTS>" in context:
            facts_section = context.split("<FACTS>")[1].split("</FACTS>")[0]
            # Split by lines and extract individual facts
            for line in facts_section.split("\n"):
                line = line.strip()
                if line and line.startswith("-"):
                    # Remove the leading dash and clean up
                    fact = line[1:].strip()
                    if fact:
                        facts.append(fact)
        elif context:
            # Fallback: split context into sentences as individual facts
            sentences = context.split(". ")
            facts = [
                (
                    sentence.strip() + "."
                    if not sentence.endswith(".")
                    else sentence.strip()
                )
                for sentence in sentences
                if len(sentence.strip()) > 10
            ][
                :5
            ]  # Limit to 5 facts

        return facts

    def get_business_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get structured business profile data for a user from Zep

        Args:
            user_id: User identifier

        Returns:
            Business profile dictionary or None if not found
        """
        try:
            # Try to get from the dedicated business data session
            business_session_id = f"business_data_{user_id}"

            try:
                memory = self.client.memory.get(session_id=business_session_id)
                if hasattr(memory, "context") and memory.context:
                    # Parse business profile from context if it contains structured data
                    context = memory.context

                    # Look for specific business profile elements in the context
                    business_profile = {}

                    # Extract business information from context using pattern matching
                    import re

                    # Define patterns for key business information
                    patterns = {
                        "biggest_challenge": r"(?:challenge|problem)[^\n]*?([^\n.]+)",
                        "employee_count": r"(?:employee|team|staff)[^\n]*?(\d+|[\w\s]+people)",
                        "revenue_range": r"(?:revenue|income|sales)[^\n]*?(\$[\w\s,.-]+|\d+[\w\s]*)",
                        "industry": r"(?:industry|sector|field)[^\n]*?([^\n.]+)",
                        "main_business_goal": r"(?:goal|objective|aim)[^\n]*?([^\n.]+)",
                    }

                    for key, pattern in patterns.items():
                        matches = re.findall(pattern, context, re.IGNORECASE)
                        if matches:
                            # Take the first meaningful match
                            value = matches[0].strip()
                            if len(value) > 3:  # Filter out very short matches
                                business_profile[key] = value

                    if business_profile:
                        logger.debug(
                            f"Extracted business profile from context for user {user_id}"
                        )
                        return business_profile

            except Exception as session_error:
                logger.debug(
                    f"Could not retrieve from business session: {session_error}"
                )

            # Fallback: Try to extract from knowledge graph facts
            try:
                knowledge_graph = self.get_user_knowledge_graph(user_id)
                if knowledge_graph and "edges" in knowledge_graph:
                    business_facts = {}

                    for edge in knowledge_graph["edges"]:
                        if isinstance(edge, dict) and "fact" in edge:
                            fact = edge["fact"]
                            fact_lower = fact.lower()

                            # Map facts to business profile fields
                            if (
                                "challenge" in fact_lower
                                and "biggest_challenge" not in business_facts
                            ):
                                business_facts["biggest_challenge"] = fact
                            elif (
                                any(
                                    word in fact_lower
                                    for word in ["employee", "team", "staff"]
                                )
                                and "employee_count" not in business_facts
                            ):
                                business_facts["employee_count"] = fact
                            elif (
                                any(
                                    word in fact_lower
                                    for word in ["revenue", "sales", "income"]
                                )
                                and "revenue_range" not in business_facts
                            ):
                                business_facts["revenue_range"] = fact
                            elif (
                                "industry" in fact_lower
                                and "industry" not in business_facts
                            ):
                                business_facts["industry"] = fact
                            elif (
                                any(
                                    word in fact_lower for word in ["goal", "objective"]
                                )
                                and "main_business_goal" not in business_facts
                            ):
                                business_facts["main_business_goal"] = fact

                    if business_facts:
                        logger.debug(
                            f"Extracted business profile from facts for user {user_id}"
                        )
                        return business_facts

            except Exception as graph_error:
                logger.debug(f"Could not extract from knowledge graph: {graph_error}")

        except Exception as e:
            logger.warning(f"Error retrieving business profile for user {user_id}: {e}")

        return None

    def get_user_knowledge_graph(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's complete knowledge graph for visualization with proper node names

        Args:
            user_id: User identifier

        Returns:
            User's knowledge graph data with nodes and edges
        """
        try:
            # Get user information
            user = self.client.user.get(user_id)

            # Get all nodes associated with this user
            nodes_response = self.client.graph.node.get_by_user_id(user_id=user_id)

            # Get all edges (facts/relationships) for this user
            edges_response = self.client.graph.edge.get_by_user_id(user_id=user_id)

            # Process nodes - extract meaningful information
            processed_nodes = []
            for node in nodes_response:
                # Handle different node attribute names based on Zep's actual API response
                node_id = (
                    getattr(node, "uuid_", None)
                    or getattr(node, "uuid", None)
                    or getattr(node, "id", None)
                    or str(node)[:8]
                )
                node_name = (
                    getattr(node, "name", None)
                    or getattr(node, "summary", None)
                    or getattr(node, "label", None)
                    or str(node_id)[:8]
                    if node_id
                    else "unknown"
                )

                node_info = {
                    "id": node_id,
                    "name": node_name,
                    "type": getattr(node, "type", None)
                    or getattr(node, "entity_type", "unknown"),
                    "summary": getattr(node, "summary", "")
                    or getattr(node, "description", ""),
                    "created_at": getattr(node, "created_at", None),
                    "metadata": getattr(node, "metadata", {}),
                    "raw_attributes": [
                        attr for attr in dir(node) if not attr.startswith("_")
                    ],  # Debug info
                }
                processed_nodes.append(node_info)

            # Process edges - extract relationships
            processed_edges = []
            for edge in edges_response:
                edge_id = (
                    getattr(edge, "uuid_", None)
                    or getattr(edge, "uuid", None)
                    or getattr(edge, "id", None)
                    or str(edge)[:8]
                )

                edge_info = {
                    "id": edge_id,
                    "source": getattr(edge, "source_node_uuid", None)
                    or getattr(edge, "source", None),
                    "target": getattr(edge, "target_node_uuid", None)
                    or getattr(edge, "target", None),
                    "relationship": getattr(edge, "relationship_type", None)
                    or getattr(edge, "relation", "related_to"),
                    "fact": getattr(edge, "fact", "")
                    or getattr(edge, "description", ""),
                    "created_at": getattr(edge, "created_at", None),
                    "valid_at": getattr(edge, "valid_at", None),
                    "raw_attributes": [
                        attr for attr in dir(edge) if not attr.startswith("_")
                    ],  # Debug info
                }
                processed_edges.append(edge_info)

            return {
                "user_id": user_id,
                "user_info": {
                    "id": user.user_id,
                    "metadata": getattr(user, "metadata", {}),
                    "created_at": getattr(user, "created_at", None),
                },
                "nodes": processed_nodes,
                "edges": processed_edges,
                "stats": {
                    "total_nodes": len(processed_nodes),
                    "total_edges": len(processed_edges),
                },
            }

        except Exception as e:
            logger.error(f"Error retrieving user knowledge graph: {str(e)}")
            return {"error": str(e)}

    def delete_user_data(self, user_id: str) -> bool:
        """
        Delete all user data from Zep (for privacy compliance)

        Args:
            user_id: User identifier

        Returns:
            True if successful
        """
        try:
            self.client.user.delete(user_id)
            logger.info(f"Deleted user data from Zep: {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting user data from Zep: {str(e)}")
            return False


# Global instance
zep_memory = ZepMemoryManager()
