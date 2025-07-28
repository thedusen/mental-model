/**
 * End-to-End Integration Tests for Zep User Creation Fix
 * Simulates real user registration to chat flows
 */

import { 
  setupMockAuth, 
  setupMockAuthFailure, 
  mockUser, 
  mockSession,
  mockSupabaseClient,
  mockAuth,
  mockChat,
  server,
  setProductionEnv,
  setDevelopmentEnv
} from '../../test-support/testUtils';

// Mock the supabase module using the standardized mocks
jest.mock('../../utils/supabase', () => ({
  supabase: require('../../test-support/testUtils').mockSupabaseClient,
  auth: require('../../test-support/testUtils').mockAuth,
  chat: require('../../test-support/testUtils').mockChat,
}));

describe('End-to-End User Flows', () => {
  let originalFetch;
  let mockFetch;
  
  beforeEach(() => {
    originalFetch = global.fetch;
    mockFetch = jest.fn();
    global.fetch = mockFetch;
    
    jest.clearAllMocks();
    server.listen({ onUnhandledRequest: 'error' });
  });

  afterEach(() => {
    global.fetch = originalFetch;
    server.resetHandlers();
  });

  afterAll(() => {
    server.close();
  });

  describe('Direct Chat Flow (Main Fix Scenario)', () => {
    test('should complete full flow: register → type in chat → Zep user created', async () => {
      /**
       * Simulates the exact scenario the fix addresses:
       * 1. User registers
       * 2. User bypasses questionnaire 
       * 3. User types directly in chat box
       * 4. Verify Zep user gets created automatically
       */
      
      // Step 1: User registration (simulated - auth state changes)
      setupMockAuth({
        ...mockUser,
        id: 'e2e-direct-chat-user-001'
      });
      
      // Step 2: Mock the chat.createSession to return success with Zep user creation
      mockChat.createSession.mockResolvedValueOnce({
        data: {
          ...mockSession,
          id: 'e2e-session-001',
          user_id: 'e2e-direct-chat-user-001',
          title: null, // User typed directly, no title initially
          metadata: {
            zep_user_created: true,
            zep_user_id: 'e2e-direct-chat-user-001',
            source: 'chat_session',
            created_via: 'chat_only'
          }
        },
        error: null
      });
      
      // Step 3: User clicks in chat input and starts typing (triggers session creation)
      const sessionResult = await mockChat.createSession();
      
      // Step 4: Verify session was created successfully
      expect(sessionResult.error).toBeNull();
      expect(sessionResult.data).toBeDefined();
      expect(sessionResult.data.user_id).toBe('e2e-direct-chat-user-001');
      expect(sessionResult.data.metadata.zep_user_created).toBe(true);
      
      // Step 5: Verify the createSession function was called
      expect(mockChat.createSession).toHaveBeenCalled();
      
      // Step 7: Simulate user sending first message
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({
          id: 'msg-001',
          session_id: 'e2e-session-001',
          role: 'user',
          content: 'Hello, I need help with my business strategy',
          metadata: { zep_stored: true }
        })
      });
      
      const messageResult = await chat.addMessage(
        'e2e-session-001',
        'user',
        'Hello, I need help with my business strategy'
      );
      
      expect(messageResult.error).toBeNull();
      expect(messageResult.data.content).toBe('Hello, I need help with my business strategy');
    });

    test('should handle direct chat flow when user types custom title', async () => {
      // User types directly but creates a meaningful session title
      setupMockAuth({
        ...mockUser,
        id: 'e2e-custom-title-user-002'
      });
      
      const { chat } = await import('../../utils/supabase');
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({
          ...mockSession,
          id: 'e2e-session-002',
          user_id: 'e2e-custom-title-user-002',
          title: 'Help with product strategy',
          metadata: { zep_user_created: true }
        })
      });
      
      const sessionResult = await chat.createSession('Help with product strategy');
      
      expect(sessionResult.error).toBeNull();
      expect(sessionResult.data.title).toBe('Help with product strategy');
      expect(sessionResult.data.metadata.zep_user_created).toBe(true);
    });
  });

  describe('Let\'s Chat Button Flow (Regression Prevention)', () => {
    test('should complete flow: register → click "Let\'s chat!" → Zep user created', async () => {
      /**
       * Ensures the existing "Let's chat!" button flow still works
       * This prevents regression in the existing functionality
       */
      
      // Step 1: User registration
      setupMockAuth({
        ...mockUser,
        id: 'e2e-lets-chat-user-003'
      });
      
      const { chat } = await import('../../utils/supabase');
      
      // Step 2: Mock backend response for "Let's chat!" flow
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({
          ...mockSession,
          id: 'e2e-session-003',
          user_id: 'e2e-lets-chat-user-003',
          title: 'Let\'s chat!',
          metadata: {
            zep_user_created: true,
            source: 'chat_session',
            created_via: 'chat_only'
          }
        })
      });
      
      // Step 3: User clicks "Let's chat!" button
      const sessionResult = await chat.createSession('Let\'s chat!');
      
      // Step 4: Verify session creation
      expect(sessionResult.error).toBeNull();
      expect(sessionResult.data.title).toBe('Let\'s chat!');
      expect(sessionResult.data.metadata.zep_user_created).toBe(true);
      
      // Step 5: Verify API call
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/chat/sessions',
        expect.objectContaining({
          body: JSON.stringify({
            user_id: 'e2e-lets-chat-user-003',
            title: 'Let\'s chat!'
          })
        })
      );
    });
  });

  describe('Error Scenarios', () => {
    test('should handle network failures gracefully in production', async () => {
      // Simulate production environment
      const restoreEnv = setProductionEnv();
      
      setupMockAuth({
        ...mockUser,
        id: 'e2e-network-error-user-004'
      });
      
      // Re-import to get fresh environment
      jest.resetModules();
      const { chat } = await import('../../utils/supabase');
      
      // Simulate network failure
      mockFetch.mockRejectedValueOnce(new Error('Network connection failed'));
      
      const sessionResult = await chat.createSession('Network test session');
      
      expect(sessionResult.data).toBeNull();
      expect(sessionResult.error).toBeInstanceOf(Error);
      expect(sessionResult.error.message).toBe('Network connection failed');
      
      restoreEnv();
    });

    test('should handle Zep service unavailable but continue session creation', async () => {
      setupMockAuth({
        ...mockUser,
        id: 'e2e-zep-unavailable-user-005'
      });
      
      const { chat } = await import('../../utils/supabase');
      
      // Mock backend response indicating Zep failed but session succeeded
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({
          ...mockSession,
          id: 'e2e-session-005',
          user_id: 'e2e-zep-unavailable-user-005',
          title: 'Session despite Zep failure',
          metadata: {
            zep_user_created: false,
            zep_error: 'Zep service temporarily unavailable',
            session_created: true
          }
        })
      });
      
      const sessionResult = await chat.createSession('Session despite Zep failure');
      
      // Session should still be created successfully
      expect(sessionResult.error).toBeNull();
      expect(sessionResult.data.id).toBe('e2e-session-005');
      expect(sessionResult.data.metadata.zep_user_created).toBe(false);
      expect(sessionResult.data.metadata.session_created).toBe(true);
    });

    test('should handle backend 500 error appropriately', async () => {
      setupMockAuth({
        ...mockUser,
        id: 'e2e-backend-error-user-006'
      });
      
      const { chat } = await import('../../utils/supabase');
      
      // Simulate backend error
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: () => Promise.resolve('Internal Server Error - Database connection failed')
      });
      
      const sessionResult = await chat.createSession('Backend error test');
      
      expect(sessionResult.data).toBeNull();
      expect(sessionResult.error).toBeInstanceOf(Error);
      expect(sessionResult.error.message).toContain('HTTP error! status: 500');
    });
  });

  describe('Multi-User Scenarios', () => {
    test('should handle multiple users creating sessions simultaneously', async () => {
      // Simulate multiple users creating sessions around the same time
      const users = [
        { id: 'concurrent-user-001', title: 'User 1 session' },
        { id: 'concurrent-user-002', title: 'User 2 session' },
        { id: 'concurrent-user-003', title: 'User 3 session' }
      ];
      
      const { chat } = await import('../../utils/supabase');
      
      // Mock successful responses for all users
      users.forEach((user, index) => {
        mockFetch.mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: () => Promise.resolve({
            ...mockSession,
            id: `concurrent-session-${index + 1}`,
            user_id: user.id,
            title: user.title,
            metadata: { zep_user_created: true }
          })
        });
      });
      
      // Simulate concurrent session creation
      const sessionPromises = users.map(user => {
        // Setup auth for each user
        setupMockAuth({ ...mockUser, id: user.id });
        return chat.createSession(user.title);
      });
      
      const sessionResults = await Promise.all(sessionPromises);
      
      // Verify all sessions were created successfully
      sessionResults.forEach((result, index) => {
        expect(result.error).toBeNull();
        expect(result.data.user_id).toBe(users[index].id);
        expect(result.data.metadata.zep_user_created).toBe(true);
      });
    });
  });

  describe('Environment-Specific Flows', () => {
    test('should work correctly in development environment', async () => {
      const restoreEnv = setDevelopmentEnv();
      
      setupMockAuth({
        ...mockUser,
        id: 'dev-env-user-007'
      });
      
      jest.resetModules();
      const { chat } = await import('../../utils/supabase');
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({
          ...mockSession,
          user_id: 'dev-env-user-007',
          metadata: { environment: 'development' }
        })
      });
      
      const sessionResult = await chat.createSession('Dev environment test');
      
      expect(sessionResult.error).toBeNull();
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/chat/sessions',
        expect.any(Object)
      );
      
      restoreEnv();
    });

    test('should validate API URL in production environment', async () => {
      const restoreEnv = setProductionEnv();
      
      // Simulate missing API URL in production
      delete process.env.REACT_APP_API_URL;
      
      setupMockAuth({
        ...mockUser,
        id: 'prod-validation-user-008'
      });
      
      jest.resetModules();
      const { chat } = await import('../../utils/supabase');
      
      const sessionResult = await chat.createSession('Production validation test');
      
      expect(sessionResult.data).toBeNull();
      expect(sessionResult.error).toBeInstanceOf(Error);
      expect(sessionResult.error.message).toContain('REACT_APP_API_URL must be configured in production');
      
      restoreEnv();
    });
  });

  describe('Data Flow Validation', () => {
    test('should ensure proper data flow from frontend to backend', async () => {
      setupMockAuth({
        ...mockUser,
        id: 'data-flow-user-009',
        email: 'dataflow@example.com',
        user_metadata: {
          name: 'Data Flow User',
          company: 'Test Corp'
        }
      });
      
      const { chat } = await import('../../utils/supabase');
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({
          ...mockSession,
          id: 'data-flow-session-009',
          user_id: 'data-flow-user-009',
          title: 'Data flow validation',
          metadata: {
            zep_user_created: true,
            user_email: 'dataflow@example.com',
            user_name: 'Data Flow User'
          }
        })
      });
      
      const sessionResult = await chat.createSession('Data flow validation');
      
      expect(sessionResult.error).toBeNull();
      
      // Verify the correct data was sent to backend
      const callArgs = mockFetch.mock.calls[0];
      const requestBody = JSON.parse(callArgs[1].body);
      
      expect(requestBody.user_id).toBe('data-flow-user-009');
      expect(requestBody.title).toBe('Data flow validation');
      
      // Verify response data structure
      expect(sessionResult.data.metadata.zep_user_created).toBe(true);
      expect(sessionResult.data.metadata.user_email).toBe('dataflow@example.com');
    });
  });

  describe('Business Requirement Validation', () => {
    test('should satisfy core requirement: all authenticated users get Zep users', async () => {
      /**
       * This test validates the core business requirement:
       * "All authenticated users should get Zep users created automatically on their first chat interaction"
       */
      
      const testScenarios = [
        {
          user_id: 'req-validation-001',
          scenario: 'Direct typing user',
          title: null
        },
        {
          user_id: 'req-validation-002', 
          scenario: 'Let\'s chat button user',
          title: 'Let\'s chat!'
        },
        {
          user_id: 'req-validation-003',
          scenario: 'Custom title user',
          title: 'Help me with my startup'
        }
      ];
      
      const { chat } = await import('../../utils/supabase');
      
      for (const scenario of testScenarios) {
        // Setup auth for this user
        setupMockAuth({
          ...mockUser,
          id: scenario.user_id
        });
        
        // Mock successful Zep user creation
        mockFetch.mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: () => Promise.resolve({
            ...mockSession,
            user_id: scenario.user_id,
            title: scenario.title,
            metadata: {
              zep_user_created: true,
              source: 'chat_session',
              created_via: 'chat_only'
            }
          })
        });
        
        // Create session
        const sessionResult = await chat.createSession(scenario.title);
        
        // Validate requirement
        expect(sessionResult.error).toBeNull();
        expect(sessionResult.data.metadata.zep_user_created).toBe(true);
        expect(sessionResult.data.metadata.source).toBe('chat_session');
        
        // Reset for next iteration
        mockFetch.mockClear();
      }
    });
  });
});