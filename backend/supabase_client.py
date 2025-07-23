"""
Supabase client configuration for backend
"""

import os
from supabase import create_client, Client
from typing import Optional

# Get Supabase configuration from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
SUPABASE_SERVICE_KEY = os.getenv(
    "SUPABASE_SERVICE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU",
)

# Initialize supabase client lazily to avoid CI failures
supabase: Optional[Client] = None


def get_supabase_client() -> Client:
    """Get or create Supabase client"""
    global supabase
    if supabase is None:
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise Exception("Supabase configuration is missing - set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables")
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
        return response.data[0] if response.data else None

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


# Create a singleton instance
supabase_service = SupabaseService()
