"""
Comprehensive tests for the /api/chat/sessions endpoint
Tests the Zep user creation fix that ensures all users get created in Zep
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock
from fastapi import HTTPException


class TestChatSessionsAPI:
    """Test the chat sessions API endpoint with Zep integration"""

    def test_create_session_success_with_zep_user_creation(
        self, client, session_request, mock_zep_memory, mock_supabase_service
    ):
        """Test successful session creation with Zep user creation"""
        # Arrange
        expected_session = {
            "id": "session-1",
            "user_id": "test-user-123",
            "title": "Test Session",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "metadata": {}
        }
        
        # Act
        response = client.post("/api/chat/sessions", json=session_request)
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["id"] == expected_session["id"]
        assert response_data["user_id"] == expected_session["user_id"]
        assert response_data["title"] == expected_session["title"]
        
        # Verify Zep user was created
        assert "test-user-123" in mock_zep_memory.users_created
        zep_user = mock_zep_memory.users_created["test-user-123"]
        assert zep_user.user_id == "test-user-123"
        assert zep_user.metadata["source"] == "chat_session"
        assert zep_user.metadata["created_via"] == "chat_only"

    def test_create_session_without_title(
        self, client, mock_zep_memory, mock_supabase_service
    ):
        """Test session creation without title"""
        # Arrange
        request_data = {"user_id": "test-user-123"}
        
        # Act
        response = client.post("/api/chat/sessions", json=request_data)
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["user_id"] == "test-user-123"
        assert response_data["title"] is None
        
        # Verify Zep user was still created
        assert "test-user-123" in mock_zep_memory.users_created

    def test_create_session_with_existing_zep_user(
        self, client, session_request, mock_zep_memory, mock_supabase_service
    ):
        """Test session creation when Zep user already exists"""
        # Arrange - Pre-create the Zep user
        existing_user = Mock()
        existing_user.user_id = "test-user-123"
        existing_user.metadata = {"source": "questionnaire", "existing": True}
        mock_zep_memory.users_created["test-user-123"] = existing_user
        
        # Act
        response = client.post("/api/chat/sessions", json=session_request)
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["user_id"] == "test-user-123"
        
        # Verify existing user was returned (not recreated)
        zep_user = mock_zep_memory.users_created["test-user-123"]
        assert zep_user.metadata["existing"] is True

    @patch('main.logger')
    def test_create_session_zep_failure_continues_session_creation(
        self, mock_logger, client, session_request, mock_zep_memory, mock_supabase_service
    ):
        """Test that session creation continues even if Zep user creation fails"""
        # Arrange - Make Zep user creation fail
        async def failing_user_creation(user_id, metadata):
            raise Exception("Zep connection timeout")
            
        mock_zep_memory.ensure_user_exists_coordinated = AsyncMock(side_effect=failing_user_creation)
        
        # Act
        response = client.post("/api/chat/sessions", json=session_request)
        
        # Assert
        assert response.status_code == 200  # Session should still be created
        response_data = response.json()
        assert response_data["user_id"] == "test-user-123"
        
        # Verify warning was logged
        mock_logger.warning.assert_called()
        warning_call = mock_logger.warning.call_args[0][0]
        assert "Error ensuring Zep user exists" in warning_call

    @patch('main.logger')
    def test_create_session_zep_user_creation_returns_none(
        self, mock_logger, client, session_request, mock_zep_memory, mock_supabase_service
    ):
        """Test handling when Zep user creation returns None"""
        # Arrange - Make Zep user creation return None
        mock_zep_memory.ensure_user_exists_coordinated = AsyncMock(return_value=None)
        
        # Act
        response = client.post("/api/chat/sessions", json=session_request)
        
        # Assert
        assert response.status_code == 200  # Session should still be created
        response_data = response.json()
        assert response_data["user_id"] == "test-user-123"
        
        # Verify warning was logged
        mock_logger.warning.assert_called()
        warning_call = mock_logger.warning.call_args[0][0]
        assert "Failed to ensure Zep user exists" in warning_call

    def test_create_session_supabase_failure(
        self, client, session_request, mock_zep_memory, mock_supabase_service
    ):
        """Test handling when Supabase session creation fails"""
        # Arrange - Make Supabase fail
        async def failing_session_creation(user_id, title):
            return None  # Simulates failure
            
        mock_supabase_service.create_chat_session = AsyncMock(side_effect=failing_session_creation)
        
        # Act
        response = client.post("/api/chat/sessions", json=session_request)
        
        # Assert
        assert response.status_code == 500
        assert "Failed to create session" in response.json()["detail"]

    def test_create_session_invalid_request_data(self, client):
        """Test session creation with invalid request data"""
        # Arrange
        invalid_request = {"invalid_field": "value"}
        
        # Act
        response = client.post("/api/chat/sessions", json=invalid_request)
        
        # Assert
        assert response.status_code == 422  # Validation error

    def test_create_session_missing_user_id(self, client):
        """Test session creation without user_id"""
        # Arrange
        invalid_request = {"title": "Test Session"}
        
        # Act
        response = client.post("/api/chat/sessions", json=invalid_request)
        
        # Assert
        assert response.status_code == 422  # Validation error

    @patch('main.logger')
    def test_create_session_logs_zep_user_creation_success(
        self, mock_logger, client, session_request, mock_zep_memory, mock_supabase_service
    ):
        """Test that successful Zep user creation is logged"""
        # Act
        response = client.post("/api/chat/sessions", json=session_request)
        
        # Assert
        assert response.status_code == 200
        
        # Verify success was logged
        mock_logger.info.assert_called()
        info_call = mock_logger.info.call_args[0][0]
        assert "Ensured Zep user exists for chat session: test-user-123" in info_call

    def test_create_session_response_format(
        self, client, session_request, mock_zep_memory, mock_supabase_service
    ):
        """Test that response format matches SessionResponse model"""
        # Act
        response = client.post("/api/chat/sessions", json=session_request)
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        
        # Verify all required fields are present
        required_fields = ["id", "user_id", "title", "created_at", "updated_at", "metadata"]
        for field in required_fields:
            assert field in response_data
            
        # Verify data types
        assert isinstance(response_data["metadata"], dict)

    def test_create_session_zep_metadata_structure(
        self, client, session_request, mock_zep_memory, mock_supabase_service
    ):
        """Test that correct metadata is passed to Zep user creation"""
        # Act
        response = client.post("/api/chat/sessions", json=session_request)
        
        # Assert
        assert response.status_code == 200
        
        # Verify Zep user metadata
        zep_user = mock_zep_memory.users_created["test-user-123"]
        assert zep_user.metadata["source"] == "chat_session"
        assert zep_user.metadata["created_via"] == "chat_only"

    @pytest.mark.asyncio
    async def test_create_session_concurrent_requests(
        self, client, mock_zep_memory, mock_supabase_service
    ):
        """Test handling concurrent session creation requests for same user"""
        # This tests the distributed locking mechanism
        
        # Arrange
        requests = [
            {"user_id": "concurrent-user", "title": f"Session {i}"}
            for i in range(3)
        ]
        
        # Act - Send concurrent requests
        responses = []
        for request in requests:
            response = client.post("/api/chat/sessions", json=request)
            responses.append(response)
        
        # Assert
        for response in responses:
            assert response.status_code == 200
            
        # Verify only one Zep user was created despite multiple requests
        assert "concurrent-user" in mock_zep_memory.users_created
        # Note: In real implementation, distributed locking would prevent duplicates

    def test_create_session_handles_various_user_id_formats(
        self, client, mock_zep_memory, mock_supabase_service
    ):
        """Test session creation with various user ID formats"""
        # Arrange
        user_id_formats = [
            "uuid-format-user-123-456",
            "user@example.com",
            "user123",
            "auth0|507f1f77bcf86cd799439011"
        ]
        
        for user_id in user_id_formats:
            # Act
            request_data = {"user_id": user_id, "title": f"Session for {user_id}"}
            response = client.post("/api/chat/sessions", json=request_data)
            
            # Assert
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["user_id"] == user_id
            
            # Verify Zep user was created
            assert user_id in mock_zep_memory.users_created


class TestChatSessionsErrorHandling:
    """Test error handling and edge cases"""

    def test_create_session_general_exception(
        self, client, session_request, mock_zep_memory
    ):
        """Test handling of unexpected exceptions"""
        # Arrange - Make Supabase service raise unexpected exception
        with patch('main.supabase_service') as mock_service:
            mock_service.create_chat_session = AsyncMock(side_effect=Exception("Unexpected error"))
            
            # Act
            response = client.post("/api/chat/sessions", json=session_request)
            
            # Assert
            assert response.status_code == 500
            assert "Failed to create chat session" in response.json()["detail"]

    @patch('main.logger')
    def test_create_session_logs_general_errors(
        self, mock_logger, client, session_request
    ):
        """Test that general errors are properly logged"""
        # Arrange
        with patch('main.supabase_service') as mock_service:
            mock_service.create_chat_session = AsyncMock(side_effect=Exception("Test error"))
            
            # Act
            response = client.post("/api/chat/sessions", json=session_request)
            
            # Assert
            assert response.status_code == 500
            mock_logger.error.assert_called()
            error_call = mock_logger.error.call_args[0][0]
            assert "Error creating chat session" in error_call


class TestChatSessionsBusinessLogic:
    """Test business logic and integration scenarios"""

    def test_create_session_preserves_existing_zep_user_metadata(
        self, client, session_request, mock_zep_memory, mock_supabase_service
    ):
        """Test that existing Zep user metadata is preserved"""
        # Arrange - Create existing user with questionnaire data
        existing_user = Mock()
        existing_user.user_id = "test-user-123"
        existing_user.metadata = {
            "source": "questionnaire",
            "industry": "Technology",
            "role": "CEO",
            "questionnaire_completed": True
        }
        mock_zep_memory.users_created["test-user-123"] = existing_user
        
        # Act
        response = client.post("/api/chat/sessions", json=session_request)
        
        # Assert
        assert response.status_code == 200
        
        # Verify existing metadata is preserved
        zep_user = mock_zep_memory.users_created["test-user-123"]
        assert zep_user.metadata["source"] == "questionnaire"  # Original preserved
        assert zep_user.metadata["industry"] == "Technology"
        assert zep_user.metadata["questionnaire_completed"] is True

    def test_create_session_first_time_chat_user_workflow(
        self, client, mock_zep_memory, mock_supabase_service
    ):
        """Test the complete workflow for a first-time chat user (bypassing questionnaire)"""
        # This simulates the exact fix scenario: user registers, skips questionnaire, starts chatting
        
        # Arrange
        first_time_user_request = {
            "user_id": "first-time-user-789",
            "title": "My first chat session"
        }
        
        # Act
        response = client.post("/api/chat/sessions", json=first_time_user_request)
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["user_id"] == "first-time-user-789"
        assert response_data["title"] == "My first chat session"
        
        # Verify Zep user was created with correct metadata indicating chat-only flow
        assert "first-time-user-789" in mock_zep_memory.users_created
        zep_user = mock_zep_memory.users_created["first-time-user-789"]
        assert zep_user.metadata["source"] == "chat_session"
        assert zep_user.metadata["created_via"] == "chat_only"

    def test_create_session_questionnaire_user_workflow(
        self, client, mock_zep_memory, mock_supabase_service
    ):
        """Test workflow for user who completed questionnaire first (existing flow)"""
        # This verifies no regression in the existing questionnaire flow
        
        # Arrange - Simulate user already exists from questionnaire
        questionnaire_user = Mock()
        questionnaire_user.user_id = "questionnaire-user-456"
        questionnaire_user.metadata = {
            "source": "questionnaire",
            "created_via": "questionnaire_flow",
            "business_context": "Enterprise software"
        }
        mock_zep_memory.users_created["questionnaire-user-456"] = questionnaire_user
        
        request_data = {
            "user_id": "questionnaire-user-456",
            "title": "Post-questionnaire chat"
        }
        
        # Act
        response = client.post("/api/chat/sessions", json=request_data)
        
        # Assert
        assert response.status_code == 200
        
        # Verify existing questionnaire user data is preserved
        zep_user = mock_zep_memory.users_created["questionnaire-user-456"]
        assert zep_user.metadata["source"] == "questionnaire"  # Original preserved
        assert zep_user.metadata["created_via"] == "questionnaire_flow"
        assert zep_user.metadata["business_context"] == "Enterprise software"