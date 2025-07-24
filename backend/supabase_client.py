"""
Supabase client configuration for backend
"""

import os
from supabase import create_client, Client
from typing import Optional

# Get Supabase configuration from environment variables
# Use localhost fallback only in development (when no production env vars are set)
SUPABASE_URL = os.getenv(
    "SUPABASE_URL",
    "http://127.0.0.1:54321" if os.getenv("NODE_ENV") != "production" else None,
)
SUPABASE_SERVICE_KEY = os.getenv(
    "SUPABASE_SERVICE_KEY",
    # Fallback to anon key for development if service key not available
    os.getenv(
        "SUPABASE_ANON_KEY",
        (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOuoJN_mz4WnKu11FU3gZoD6p8LTOgXhHO6M"
            if os.getenv("NODE_ENV") != "production"
            else None
        ),
    ),
)

# Initialize supabase client lazily to avoid CI failures
supabase: Optional[Client] = None


def get_supabase_client() -> Client:
    """Get or create Supabase client"""
    global supabase
    if supabase is None:
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise Exception(
                "Supabase configuration is missing - set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables"
            )
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return supabase


class SupabaseService:
    """Service class for Supabase operations"""

    def __init__(self):
        self._client = None

    @property
    def client(self) -> Client:
        """Get supabase client with lazy initialization"""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    async def get_user_by_id(self, user_id: str):
        """Get user profile by ID"""
        response = (
            self.client.table("user_profiles").select("*").eq("id", user_id).execute()
        )
        return response.data[0] if response.data else None

    async def create_chat_session(self, user_id: str, title: Optional[str] = None):
        """Create a new chat session"""
        data = {"user_id": user_id, "title": title}
        response = self.client.table("chat_sessions").insert(data).execute()
        return response.data[0] if response.data else None

    async def get_user_sessions(self, user_id: str, limit: int = 50, offset: int = 0):
        """Get all chat sessions for a user"""
        response = (
            self.client.table("chat_sessions")
            .select("*")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
            .limit(limit)
            .offset(offset)
            .execute()
        )
        return response.data

    async def get_session_messages(self, session_id: str, limit: int = 100):
        """Get messages for a chat session"""
        response = (
            self.client.table("chat_messages")
            .select("*")
            .eq("session_id", session_id)
            .order("timestamp", desc=False)
            .limit(limit)
            .execute()
        )
        return response.data

    async def add_message(
        self, session_id: str, role: str, content: str, metadata: dict = None
    ):
        """Add a message to a chat session"""
        data = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "metadata": metadata or {},
        }
        response = self.client.table("chat_messages").insert(data).execute()

        # Update the session's updated_at timestamp to maintain proper ordering
        if response.data:
            self.client.table("chat_sessions").update({"updated_at": "now()"}).eq(
                "id", session_id
            ).execute()

        return response.data[0] if response.data else None

    async def get_session(self, session_id: str):
        """Get a single chat session by ID"""
        response = (
            self.client.table("chat_sessions")
            .select("*")
            .eq("id", session_id)
            .single()
            .execute()
        )
        return response.data if response.data else None

    async def update_session(self, session_id: str, updates: dict):
        """Update a chat session"""
        response = (
            self.client.table("chat_sessions")
            .update(updates)
            .eq("id", session_id)
            .execute()
        )
        return response.data[0] if response.data else None

    async def delete_session(self, session_id: str):
        """Delete a chat session and all its messages"""
        response = (
            self.client.table("chat_sessions").delete().eq("id", session_id).execute()
        )
        return response.data

    async def search_messages(self, user_id: str, query: str, limit: int = 20):
        """Search messages across all user sessions"""
        # Note: This requires a custom RPC function for full-text search across sessions
        # For now, we'll implement a simple search
        sessions = await self.get_user_sessions(user_id, limit=100)
        session_ids = [s["id"] for s in sessions]

        if not session_ids:
            return []

        # Search messages in user's sessions
        response = (
            self.client.table("chat_messages")
            .select("*, chat_sessions(title)")
            .in_("session_id", session_ids)
            .ilike("content", f"%{query}%")
            .limit(limit)
            .execute()
        )

        return response.data

    # Business Profile Methods
    async def get_business_profile_questions(self):
        """Get all business profile questions"""
        response = (
            self.client.table("business_profile_questions")
            .select("*")
            .eq("is_active", True)
            .order("order_index")
            .execute()
        )
        return response.data

    async def get_business_profile_progress(self, user_id: str):
        """Get user's business profile progress"""
        try:
            response = (
                self.client.table("user_questionnaire_progress")
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )
            # Return first result if exists, None otherwise
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error getting business profile progress for user {user_id}: {e}")
            return None

    async def get_business_profile_answers(self, user_id: str):
        """Get user's business profile answers"""
        response = (
            self.client.table("user_business_profiles")
            .select("*")
            .eq("user_id", user_id)
            .order("question_id")
            .execute()
        )
        return response.data

    async def save_business_profile_answer(
        self,
        user_id: str,
        question_id: int,
        answer: str,
        answered_at: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        """Save or update a business profile answer"""
        from datetime import datetime

        answered_at = answered_at or datetime.now().isoformat()

        # Get the question text from the questions table
        question_response = (
            self.client.table("business_profile_questions")
            .select("question_text, answer_type")
            .eq("id", question_id)
            .single()
            .execute()
        )

        if not question_response.data:
            raise Exception(f"Question with id {question_id} not found")

        question_data = question_response.data

        data = {
            "user_id": user_id,
            "question_id": question_id,
            "question_text": question_data["question_text"],
            "answer": answer,
            "answer_type": question_data["answer_type"],
            "answered_at": answered_at,
            "session_id": session_id,
            "is_complete": True,
        }

        # Use upsert to handle both insert and update cases
        response = (
            self.client.table("user_business_profiles")
            .upsert(data, on_conflict="user_id,question_id")
            .execute()
        )
        return response.data[0] if response.data else None

    async def mark_answers_synced_to_zep(self, user_id: str):
        """Mark user's business profile answers as synced to Zep"""
        from datetime import datetime

        response = (
            self.client.table("user_business_profiles")
            .update({"synced_to_zep": True, "zep_sync_at": datetime.now().isoformat()})
            .eq("user_id", user_id)
            .execute()
        )
        return response.data

    async def record_nudge_dismissed(self, user_id: str):
        """Record that user dismissed a nudge"""
        from datetime import datetime

        # First, get current progress
        try:
            progress = await self.get_business_profile_progress(user_id)
        except Exception as e:
            print(
                f"Error getting progress during nudge dismissal for user {user_id}: {e}"
            )
            progress = None

        if progress:
            # Update existing progress record
            response = (
                self.client.table("user_questionnaire_progress")
                .update(
                    {
                        "nudge_dismissed_count": progress.get(
                            "nudge_dismissed_count", 0
                        )
                        + 1,
                        "last_nudged_at": datetime.now().isoformat(),
                    }
                )
                .eq("user_id", user_id)
                .execute()
            )
        else:
            # Create initial progress record
            response = (
                self.client.table("user_questionnaire_progress")
                .insert(
                    {
                        "user_id": user_id,
                        "nudge_dismissed_count": 1,
                        "last_nudged_at": datetime.now().isoformat(),
                    }
                )
                .execute()
            )

        return response.data


# Create a singleton instance
supabase_service = SupabaseService()
