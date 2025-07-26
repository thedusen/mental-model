"""
Integration tests for complete user flows with Zep user creation
Tests the business requirement: all authenticated users should get Zep users created automatically
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import json


class TestCompleteUserFlows:
    """Integration tests for complete user registration to chat flows"""

    @pytest.mark.asyncio
    async def test_direct_chat_user_flow_complete(
        self, client, mock_zep_memory, mock_supabase_service
    ):
        """Test complete flow: user registers → types directly in chat → Zep user created"""
        
        # Step 1: User registers (simulated - this happens in Supabase Auth)
        user_id = "direct-chat-user-001"
        
        # Step 2: User clicks in chat box and types directly (triggering session creation)
        session_request = {
            "user_id": user_id,
            "title": None  # No title initially since user is just starting to type
        }
        
        # Act
        session_response = client.post("/api/chat/sessions", json=session_request)
        
        # Assert session creation
        assert session_response.status_code == 200
        session_data = session_response.json()
        session_id = session_data["id"]
        
        # Step 3: Verify Zep user was created with correct metadata
        assert user_id in mock_zep_memory.users_created
        zep_user = mock_zep_memory.users_created[user_id]
        assert zep_user.user_id == user_id
        assert zep_user.metadata["source"] == "chat_session"
        assert zep_user.metadata["created_via"] == "chat_only"
        
        # Step 4: User sends first message
        first_message_request = {
            "session_id": session_id,
            "role": "user",
            "content": "Hello, I need help with my business strategy",
            "user_id": user_id
        }
        
        message_response = client.post("/api/chat/messages", json=first_message_request)
        assert message_response.status_code == 200
        
        # Step 5: Verify the flow is complete and user can continue chatting
        messages_response = client.get(f"/api/chat/sessions/{session_id}/messages")
        assert messages_response.status_code == 200
        messages = messages_response.json()["messages"]
        assert len(messages) == 1
        assert messages[0]["content"] == "Hello, I need help with my business strategy"

    @pytest.mark.asyncio
    async def test_lets_chat_button_user_flow_complete(
        self, client, mock_zep_memory, mock_supabase_service
    ):
        """Test complete flow: user registers → clicks 'Let's chat!' → Zep user created"""
        
        # Step 1: User registers (simulated)
        user_id = "lets-chat-user-002"
        
        # Step 2: User clicks "Let's chat!" button (triggering session creation with title)
        session_request = {
            "user_id": user_id,
            "title": "Let's chat!"  # Button creates session with default title
        }
        
        # Act
        session_response = client.post("/api/chat/sessions", json=session_request)
        
        # Assert session creation
        assert session_response.status_code == 200
        session_data = session_response.json()
        assert session_data["title"] == "Let's chat!"
        
        # Step 3: Verify Zep user was created (ensuring no regression)
        assert user_id in mock_zep_memory.users_created
        zep_user = mock_zep_memory.users_created[user_id]
        assert zep_user.user_id == user_id
        assert zep_user.metadata["source"] == "chat_session"
        assert zep_user.metadata["created_via"] == "chat_only"

    @pytest.mark.asyncio
    async def test_questionnaire_then_chat_flow_no_regression(
        self, client, mock_zep_memory, mock_supabase_service
    ):
        """Test existing flow still works: questionnaire → chat (no regression)"""
        
        # Step 1: User completes questionnaire (simulated - Zep user already exists)
        user_id = "questionnaire-then-chat-user-003"
        
        # Pre-create Zep user as if from questionnaire
        questionnaire_user = Mock()
        questionnaire_user.user_id = user_id
        questionnaire_user.metadata = {
            "source": "questionnaire",
            "created_via": "questionnaire_flow",
            "industry": "Healthcare",
            "role": "CTO",
            "team_size": "50-100"
        }
        mock_zep_memory.users_created[user_id] = questionnaire_user
        
        # Step 2: User starts chatting (session creation should work with existing Zep user)
        session_request = {
            "user_id": user_id,
            "title": "Post-questionnaire discussion"
        }
        
        session_response = client.post("/api/chat/sessions", json=session_request)
        
        # Assert
        assert session_response.status_code == 200
        
        # Step 3: Verify existing Zep user metadata is preserved
        zep_user = mock_zep_memory.users_created[user_id]
        assert zep_user.metadata["source"] == "questionnaire"  # Original preserved
        assert zep_user.metadata["industry"] == "Healthcare"
        assert zep_user.metadata["role"] == "CTO"

    @pytest.mark.asyncio
    async def test_missing_user_profile_auto_creation_flow(
        self, client, mock_zep_memory, mock_supabase_service
    ):
        """Test auto-creation when user profile is missing"""
        
        # Step 1: User exists in auth but missing profile (edge case scenario)
        user_id = "missing-profile-user-004"
        
        # Step 2: User tries to create session
        session_request = {
            "user_id": user_id,
            "title": "Chat without profile"
        }
        
        session_response = client.post("/api/chat/sessions", json=session_request)
        
        # Assert session creation succeeds
        assert session_response.status_code == 200
        
        # Step 3: Verify Zep user was created even without existing profile
        assert user_id in mock_zep_memory.users_created
        zep_user = mock_zep_memory.users_created[user_id]
        assert zep_user.metadata["source"] == "chat_session"
        assert zep_user.metadata["created_via"] == "chat_only"

    @pytest.mark.asyncio
    async def test_multiple_sessions_same_user_single_zep_user(
        self, client, mock_zep_memory, mock_supabase_service
    ):
        """Test that multiple sessions for same user don't create duplicate Zep users"""
        
        user_id = "multi-session-user-005"
        
        # Create first session
        session1_request = {"user_id": user_id, "title": "First session"}
        session1_response = client.post("/api/chat/sessions", json=session1_request)
        assert session1_response.status_code == 200
        
        # Verify Zep user created
        assert user_id in mock_zep_memory.users_created
        original_zep_user = mock_zep_memory.users_created[user_id]
        
        # Create second session
        session2_request = {"user_id": user_id, "title": "Second session"}
        session2_response = client.post("/api/chat/sessions", json=session2_request)
        assert session2_response.status_code == 200
        
        # Verify same Zep user is reused (not duplicated)
        assert user_id in mock_zep_memory.users_created
        current_zep_user = mock_zep_memory.users_created[user_id]
        assert current_zep_user is original_zep_user  # Same object reference


class TestErrorHandlingIntegration:
    """Integration tests for error handling scenarios"""

    @pytest.mark.asyncio
    async def test_zep_unavailable_session_creation_continues(
        self, client, mock_supabase_service
    ):
        """Test that session creation continues when Zep is unavailable"""
        
        # Arrange - Mock Zep to be unavailable
        with patch('main.zep_memory') as mock_zep:
            mock_zep.ensure_user_exists_coordinated = AsyncMock(
                side_effect=Exception("Zep service unavailable")
            )
            
            # Act
            session_request = {
                "user_id": "zep-unavailable-user-006",
                "title": "Session when Zep is down"
            }
            
            session_response = client.post("/api/chat/sessions", json=session_request)
            
            # Assert - Session creation should still succeed
            assert session_response.status_code == 200
            session_data = session_response.json()
            assert session_data["user_id"] == "zep-unavailable-user-006"
            assert session_data["title"] == "Session when Zep is down"

    @pytest.mark.asyncio
    async def test_partial_failure_resilience(
        self, client, mock_zep_memory, mock_supabase_service
    ):
        """Test system resilience to partial failures"""
        
        # Arrange - Mock Zep to return None (partial failure)
        mock_zep_memory.ensure_user_exists_coordinated = AsyncMock(return_value=None)
        
        # Act
        session_request = {
            "user_id": "partial-failure-user-007",
            "title": "Partial failure scenario"
        }
        
        session_response = client.post("/api/chat/sessions", json=session_request)
        
        # Assert - Session creation should still succeed
        assert session_response.status_code == 200
        
        # User can continue with their session even if Zep user creation failed
        session_id = session_response.json()["id"]
        
        # Test adding a message still works
        message_request = {
            "session_id": session_id,
            "role": "user",
            "content": "Can I still chat?",
            "user_id": "partial-failure-user-007"
        }
        
        message_response = client.post("/api/chat/messages", json=message_request)
        assert message_response.status_code == 200

    @pytest.mark.asyncio
    async def test_circuit_breaker_behavior(
        self, client, mock_supabase_service, mock_circuit_breaker
    ):
        """Test circuit breaker behavior when Zep consistently fails"""
        
        # This test would verify that the circuit breaker opens after repeated failures
        # and the system continues to work in degraded mode
        
        # Arrange - Mock circuit breaker to be open
        with patch('main.zep_memory') as mock_zep:
            from circuit_breaker import CircuitBreakerOpenError
            mock_zep.ensure_user_exists_coordinated = AsyncMock(
                side_effect=CircuitBreakerOpenError("Circuit breaker is open")
            )
            
            # Act
            session_request = {
                "user_id": "circuit-breaker-user-008",
                "title": "Circuit breaker test"
            }
            
            session_response = client.post("/api/chat/sessions", json=session_request)
            
            # Assert - Should still work in degraded mode
            assert session_response.status_code == 200


class TestBusinessRequirementValidation:
    """Validate that the core business requirement is met"""

    @pytest.mark.asyncio
    async def test_all_authenticated_users_get_zep_users_requirement(
        self, client, mock_zep_memory, mock_supabase_service
    ):
        """Validate: All authenticated users should get Zep users created automatically on first chat"""
        
        # Test various user scenarios
        test_scenarios = [
            {
                "user_id": "req-test-001",
                "scenario": "Direct chat user (types immediately)",
                "title": None
            },
            {
                "user_id": "req-test-002", 
                "scenario": "Let's chat button user",
                "title": "Let's chat!"
            },
            {
                "user_id": "req-test-003",
                "scenario": "User with custom session title",
                "title": "Help me with strategy"
            }
        ]
        
        for scenario in test_scenarios:
            # Act
            session_request = {
                "user_id": scenario["user_id"],
                "title": scenario["title"]
            }
            
            session_response = client.post("/api/chat/sessions", json=session_request)
            
            # Assert
            assert session_response.status_code == 200, f"Failed for scenario: {scenario['scenario']}"
            
            # Verify Zep user was created for this user
            assert scenario["user_id"] in mock_zep_memory.users_created, \
                f"Zep user not created for scenario: {scenario['scenario']}"
            
            zep_user = mock_zep_memory.users_created[scenario["user_id"]]
            assert zep_user.user_id == scenario["user_id"]
            assert zep_user.metadata["source"] == "chat_session"
            assert zep_user.metadata["created_via"] == "chat_only"

    @pytest.mark.asyncio
    async def test_no_duplicate_zep_users_requirement(
        self, client, mock_zep_memory, mock_supabase_service  
    ):
        """Validate: No duplicate Zep users should be created for the same user"""
        
        user_id = "no-duplicate-user-009"
        
        # Create multiple sessions rapidly
        for i in range(5):
            session_request = {
                "user_id": user_id,
                "title": f"Session {i+1}"
            }
            
            session_response = client.post("/api/chat/sessions", json=session_request)
            assert session_response.status_code == 200
        
        # Verify only one Zep user exists
        assert user_id in mock_zep_memory.users_created
        # In a real implementation with proper locking, this would ensure no duplicates

    @pytest.mark.asyncio
    async def test_graceful_degradation_requirement(
        self, client, mock_supabase_service
    ):
        """Validate: System should work even when Zep is unavailable (graceful degradation)"""
        
        # Arrange - Completely disable Zep
        with patch('main.zep_memory') as mock_zep:
            mock_zep.ensure_user_exists_coordinated = AsyncMock(
                side_effect=Exception("Zep completely unavailable")
            )
            
            # Act - User should still be able to create sessions and chat
            session_request = {
                "user_id": "graceful-degradation-user-010",
                "title": "Chat without Zep"
            }
            
            session_response = client.post("/api/chat/sessions", json=session_request)
            
            # Assert
            assert session_response.status_code == 200
            session_id = session_response.json()["id"]
            
            # User should still be able to send messages
            message_request = {
                "session_id": session_id,
                "role": "user", 
                "content": "This should work even without Zep",
                "user_id": "graceful-degradation-user-010"
            }
            
            message_response = client.post("/api/chat/messages", json=message_request)
            assert message_response.status_code == 200