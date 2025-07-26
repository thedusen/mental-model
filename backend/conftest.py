"""
Pytest configuration and fixtures for backend tests
"""

import pytest
import os
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from typing import Dict, Any, Optional

# Set test environment variables before importing the app
os.environ['ANTHROPIC_API_KEY'] = 'test-key'
os.environ['COHERE_API_KEY'] = 'test-key'
os.environ['ZEP_API_KEY'] = 'test-key'
os.environ['NEO4J_URI'] = 'bolt://localhost:7687'
os.environ['NEO4J_USERNAME'] = 'neo4j'
os.environ['NEO4J_PASSWORD'] = 'test-password'
os.environ['SUPABASE_URL'] = 'http://localhost:54321'
os.environ['SUPABASE_SERVICE_KEY'] = 'test-service-key'

# Mock external services before importing main
class MockZepMemory:
    def __init__(self):
        self.enabled = True
        self.users_created = {}
        
    async def ensure_user_exists_coordinated(self, user_id: str, metadata: Optional[Dict] = None):
        """Mock Zep user creation"""
        if user_id in self.users_created:
            return self.users_created[user_id]
            
        # Simulate user creation
        user = Mock()
        user.user_id = user_id
        user.metadata = metadata or {}
        self.users_created[user_id] = user
        return user
        
    def get_business_profile(self, user_id: str):
        """Mock business profile retrieval"""
        return {
            "company_name": "Test Company",
            "industry": "Technology",
            "role": "CEO"
        }
        
    async def add_message(self, user_id: str, session_id: str, message: str, role: str = "user"):
        """Mock message storage"""
        return True

class MockSupabaseService:
    def __init__(self):
        self.sessions = {}
        self.messages = {}
        
    async def create_chat_session(self, user_id: str, title: Optional[str] = None):
        """Mock session creation"""
        session_id = f"session-{len(self.sessions) + 1}"
        session = {
            "id": session_id,
            "user_id": user_id,
            "title": title,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "metadata": {}
        }
        self.sessions[session_id] = session
        return session
        
    async def get_user_sessions(self, user_id: str, limit: int = 50, offset: int = 0):
        """Mock getting user sessions"""
        user_sessions = [s for s in self.sessions.values() if s["user_id"] == user_id]
        return user_sessions[offset:offset + limit]
        
    async def get_session_messages(self, session_id: str, limit: int = 100):
        """Mock getting session messages"""
        return self.messages.get(session_id, [])
        
    async def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None):
        """Mock adding message"""
        if session_id not in self.messages:
            self.messages[session_id] = []
            
        message = {
            "id": f"msg-{len(self.messages[session_id]) + 1}",
            "session_id": session_id,
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": "2024-01-01T00:00:00Z"
        }
        self.messages[session_id].append(message)
        return message

@pytest.fixture
def mock_zep_memory():
    """Provide mock Zep memory service"""
    return MockZepMemory()

@pytest.fixture  
def mock_supabase_service():
    """Provide mock Supabase service"""
    return MockSupabaseService()

@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver"""
    mock_driver = Mock()
    mock_session = Mock()
    mock_result = Mock()
    
    # Configure the mock chain
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_session.run.return_value = mock_result
    mock_result.data.return_value = []
    
    return mock_driver

@pytest.fixture
def app_with_mocks(mock_zep_memory, mock_supabase_service, mock_neo4j_driver):
    """Create FastAPI app with all external dependencies mocked"""
    
    with patch('main.zep_memory', mock_zep_memory), \
         patch('main.supabase_service', mock_supabase_service), \
         patch('config.get_db_session') as mock_get_db:
        
        mock_get_db.return_value = mock_neo4j_driver
        
        # Import main after patching
        from main import app
        yield app

@pytest.fixture
def client(app_with_mocks):
    """FastAPI test client with mocked dependencies"""
    return TestClient(app_with_mocks)

@pytest.fixture
def test_user():
    """Test user data"""
    return {
        "id": "test-user-123",
        "email": "test@example.com",
        "created_at": "2024-01-01T00:00:00Z"
    }

@pytest.fixture
def session_request():
    """Test session request data"""
    return {
        "user_id": "test-user-123",
        "title": "Test Session"
    }

@pytest.fixture
def mock_circuit_breaker():
    """Mock circuit breaker to always allow operations"""
    with patch('circuit_breaker.circuit_breaker_decorator') as mock_decorator:
        # Make the decorator a pass-through
        mock_decorator.side_effect = lambda *args, **kwargs: lambda func: func
        yield mock_decorator

# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()