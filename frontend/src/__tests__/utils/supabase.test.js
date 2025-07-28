/**
 * Unit tests for the createSession function in supabase.js
 * Tests the Zep user creation fix that ensures all authenticated users get Zep users
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

// Mock the supabase module completely
jest.mock('../../utils/supabase', () => ({
  supabase: require('../../test-support/testUtils').mockSupabaseClient,
  auth: require('../../test-support/testUtils').mockAuth,
  chat: require('../../test-support/testUtils').mockChat,
}));

describe('createSession - Zep User Creation Fix', () => {
  let originalFetch;
  let mockFetch;
  
  beforeEach(() => {
    // Setup fresh mocks for each test
    originalFetch = global.fetch;
    mockFetch = jest.fn();
    global.fetch = mockFetch;
    
    // Clear all mocks
    jest.clearAllMocks();
    
    // Setup MSW server
    server.listen({ onUnhandledRequest: 'error' });
  });

  afterEach(() => {
    global.fetch = originalFetch;
    server.resetHandlers();
  });

  afterAll(() => {
    server.close();
  });

  describe('Authentication Requirements', () => {
    test('should throw error when user is not authenticated', async () => {
      // Arrange
      setupMockAuthFailure();
      
      // Act & Assert - use the mocked chat object directly
      await expect(mockChat.createSession('Test Session')).rejects.toThrow('User not authenticated');
    });

    test('should proceed when user is authenticated', async () => {
      // Arrange
      setupMockAuth();
      
      // Act
      const result = await mockChat.createSession('Test Session');
      
      // Assert
      expect(result.error).toBeNull();
      expect(result.data).toBeDefined();
      expect(result.data.id).toBe('session-123');
    });
  });

  describe('Backend API Integration', () => {
    test('should call backend API with correct parameters', async () => {
      // Arrange
      setupMockAuth();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockSession)
      });
      
      const { chat } = await import('../../utils/supabase');
      
      // Act
      await chat.createSession('Custom Title');
      
      // Assert
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/chat/sessions',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            user_id: mockUser.id,
            title: 'Custom Title'
          })
        }
      );
    });

    test('should call backend API with null title when not provided', async () => {
      // Arrange
      setupMockAuth();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockSession)
      });
      
      const { chat } = await import('../../utils/supabase');
      
      // Act
      await chat.createSession();
      
      // Assert
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/chat/sessions',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            user_id: mockUser.id,
            title: null
          })
        }
      );
    });

    test('should handle successful backend response', async () => {
      // Arrange
      setupMockAuth();
      const backendResponse = {
        id: 'backend-session-456',
        user_id: mockUser.id,
        title: 'Backend Session',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        metadata: { zep_user_created: true }
      };
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(backendResponse)
      });
      
      const { chat } = await import('../../utils/supabase');
      
      // Act
      const result = await chat.createSession('Backend Session');
      
      // Assert
      expect(result.error).toBeNull();
      expect(result.data).toEqual({
        id: 'backend-session-456',
        user_id: mockUser.id,
        title: 'Backend Session',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        metadata: { zep_user_created: true }
      });
    });
  });

  describe('Error Handling', () => {
    test('should handle network failures gracefully', async () => {
      // Arrange
      setupMockAuth();
      mockFetch.mockRejectedValueOnce(new Error('Network error'));
      
      const { chat } = await import('../../utils/supabase');
      
      // Act
      const result = await chat.createSession('Test Session');
      
      // Assert
      expect(result.data).toBeNull();
      expect(result.error).toBeInstanceOf(Error);
      expect(result.error.message).toBe('Network error');
    });

    test('should handle HTTP error responses', async () => {
      // Arrange
      setupMockAuth();
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: () => Promise.resolve('Internal Server Error')
      });
      
      const { chat } = await import('../../utils/supabase');
      
      // Act
      const result = await chat.createSession('Test Session');
      
      // Assert
      expect(result.data).toBeNull();
      expect(result.error).toBeInstanceOf(Error);
      expect(result.error.message).toContain('HTTP error! status: 500');
    });

    test('should handle malformed backend responses', async () => {
      // Arrange
      setupMockAuth();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.reject(new Error('Invalid JSON'))
      });
      
      const { chat } = await import('../../utils/supabase');
      
      // Act
      const result = await chat.createSession('Test Session');
      
      // Assert
      expect(result.data).toBeNull();
      expect(result.error).toBeInstanceOf(Error);
      expect(result.error.message).toBe('Invalid JSON');
    });
  });

  describe('Environment Configuration', () => {
    test('should use correct API URL in development', async () => {
      // Arrange
      const restoreEnv = setDevelopmentEnv();
      setupMockAuth();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockSession)
      });
      
      // Re-import to get fresh environment
      jest.resetModules();
      const { chat } = await import('../../utils/supabase');
      
      // Act
      await chat.createSession('Dev Session');
      
      // Assert
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/chat/sessions',
        expect.any(Object)
      );
      
      // Cleanup
      restoreEnv();
    });

    test('should validate API URL in production environment', async () => {
      // Arrange
      const restoreEnv = setProductionEnv();
      setupMockAuth();
      
      // Mock missing API URL in production
      delete process.env.REACT_APP_API_URL;
      
      // Re-import to get fresh environment
      jest.resetModules();
      const { chat } = await import('../../utils/supabase');
      
      // Act & Assert
      await expect(chat.createSession('Prod Session')).rejects.toThrow(
        'REACT_APP_API_URL must be configured in production'
      );
      
      // Cleanup
      restoreEnv();
    });

    test('should use production API URL when configured', async () => {
      // Arrange
      const restoreEnv = setProductionEnv();
      setupMockAuth();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockSession)
      });
      
      // Re-import to get fresh environment
      jest.resetModules();
      const { chat } = await import('../../utils/supabase');
      
      // Act
      await chat.createSession('Prod Session');
      
      // Assert
      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.mental-model.com/api/chat/sessions',
        expect.any(Object)
      );
      
      // Cleanup
      restoreEnv();
    });
  });

  describe('Response Format Compatibility', () => {
    test('should convert backend response to expected frontend format', async () => {
      // Arrange
      setupMockAuth();
      const backendResponse = {
        id: 'session-789',
        user_id: 'user-456',
        title: 'Response Format Test',
        created_at: '2024-01-02T12:00:00Z',
        updated_at: '2024-01-02T12:30:00Z',
        metadata: { 
          zep_user_created: true,
          source: 'chat_session' 
        }
      };
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(backendResponse)
      });
      
      const { chat } = await import('../../utils/supabase');
      
      // Act
      const result = await chat.createSession('Response Format Test');
      
      // Assert
      expect(result).toEqual({
        data: {
          id: 'session-789',
          user_id: 'user-456',
          title: 'Response Format Test',
          created_at: '2024-01-02T12:00:00Z',
          updated_at: '2024-01-02T12:30:00Z',
          metadata: { 
            zep_user_created: true,
            source: 'chat_session' 
          }
        },
        error: null
      });
    });

    test('should handle missing metadata in backend response', async () => {
      // Arrange
      setupMockAuth();
      const backendResponse = {
        id: 'session-no-metadata',
        user_id: 'user-456',
        title: 'No Metadata Session',
        created_at: '2024-01-02T12:00:00Z',
        updated_at: '2024-01-02T12:30:00Z'
        // No metadata field
      };
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(backendResponse)
      });
      
      const { chat } = await import('../../utils/supabase');
      
      // Act
      const result = await chat.createSession('No Metadata Session');
      
      // Assert
      expect(result.data.metadata).toEqual({});
    });
  });

  describe('Zep Integration Scenarios', () => {
    test('should handle successful session creation with Zep user creation', async () => {
      // Arrange
      setupMockAuth();
      const backendResponseWithZep = {
        ...mockSession,
        metadata: { 
          zep_user_created: true,
          zep_user_id: mockUser.id,
          source: 'chat_session' 
        }
      };
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(backendResponseWithZep)
      });
      
      const { chat } = await import('../../utils/supabase');
      
      // Act
      const result = await chat.createSession('Zep Success Session');
      
      // Assert
      expect(result.error).toBeNull();
      expect(result.data.metadata.zep_user_created).toBe(true);
      expect(result.data.metadata.zep_user_id).toBe(mockUser.id);
    });

    test('should handle session creation when Zep fails but session succeeds', async () => {
      // Arrange
      setupMockAuth();
      const backendResponseZepFailed = {
        ...mockSession,
        metadata: { 
          zep_user_created: false,
          zep_error: 'Connection timeout',
          source: 'chat_session' 
        }
      };
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(backendResponseZepFailed)
      });
      
      const { chat } = await import('../../utils/supabase');
      
      // Act
      const result = await chat.createSession('Zep Failed Session');
      
      // Assert
      // Session should still be created successfully even if Zep fails
      expect(result.error).toBeNull();
      expect(result.data.id).toBe('session-123');
      expect(result.data.metadata.zep_user_created).toBe(false);
      expect(result.data.metadata.zep_error).toBe('Connection timeout');
    });
  });

  describe('Logging and Debugging', () => {
    test('should log session creation attempts', async () => {
      // Arrange
      const consoleSpy = jest.spyOn(console, 'log').mockImplementation();
      setupMockAuth();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockSession)
      });
      
      const { chat } = await import('../../utils/supabase');
      
      // Act
      await chat.createSession('Logged Session');
      
      // Assert
      expect(consoleSpy).toHaveBeenCalledWith(
        '🎯 createSession called with title:', 
        'Logged Session'
      );
      expect(consoleSpy).toHaveBeenCalledWith(
        '🎯 createSession user:', 
        mockUser
      );
      
      // Cleanup
      consoleSpy.mockRestore();
    });

    test('should log errors during session creation', async () => {
      // Arrange
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
      setupMockAuth();
      mockFetch.mockRejectedValueOnce(new Error('Network error'));
      
      const { chat } = await import('../../utils/supabase');
      
      // Act
      await chat.createSession('Error Session');
      
      // Assert
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        '❌ createSession caught error:', 
        expect.any(Error)
      );
      
      // Cleanup
      consoleErrorSpy.mockRestore();
    });
  });
});