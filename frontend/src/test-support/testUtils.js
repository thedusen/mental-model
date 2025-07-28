/**
 * Test utilities and mocks for Zep user creation tests
 */

import { rest } from 'msw';
import { setupServer } from 'msw/node';

// Mock Supabase client - matches the actual client structure
export const mockSupabaseClient = {
  auth: {
    signUp: jest.fn(),
    signInWithPassword: jest.fn(),
    signOut: jest.fn(),
    getSession: jest.fn(),
    getUser: jest.fn(),
    onAuthStateChange: jest.fn(),
    signInWithOAuth: jest.fn(),
    refreshSession: jest.fn(),
  },
  from: jest.fn(() => ({
    select: jest.fn().mockReturnThis(),
    eq: jest.fn().mockReturnThis(),
    order: jest.fn().mockReturnThis(),
    range: jest.fn().mockReturnThis(),
    limit: jest.fn().mockReturnThis(),
    insert: jest.fn().mockReturnThis(),
    update: jest.fn().mockReturnThis(),
    delete: jest.fn().mockReturnThis(),
    single: jest.fn(),
    execute: jest.fn(),
    ilike: jest.fn().mockReturnThis(),
    in: jest.fn().mockReturnThis(),
  })),
};

// Mock auth object - matches the actual auth export structure
export const mockAuth = {
  signUp: jest.fn(),
  signIn: jest.fn(),
  signOut: jest.fn(),
  getUser: jest.fn(),
  getSession: jest.fn(),
  onAuthStateChange: jest.fn(),
  signInWithGoogle: jest.fn(),
  refreshSession: jest.fn(),
};

// Mock chat object - matches the actual chat export structure  
export const mockChat = {
  createSession: jest.fn(),
  getUserSessions: jest.fn(),
  getMessages: jest.fn(),
  addMessage: jest.fn(),
  searchMessages: jest.fn(),
};

// Mock user data
export const mockUser = {
  id: 'test-user-123',
  email: 'test@example.com',
  created_at: '2024-01-01T00:00:00Z',
  user_metadata: {
    name: 'Test User'
  }
};

// Mock session data
export const mockSession = {
  id: 'session-123',
  user_id: 'test-user-123',
  title: 'Test Session',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  metadata: {}
};

// API response handlers for MSW
export const handlers = [
  // Successful session creation
  rest.post('http://localhost:8000/api/chat/sessions', (req, res, ctx) => {
    return res(ctx.json(mockSession));
  }),

  // Session creation with network error simulation
  rest.post('http://localhost:8000/api/chat/sessions-error', (req, res, ctx) => {
    return res(ctx.status(500));
  }),

  // Session creation with Zep failure but successful session creation
  rest.post('http://localhost:8000/api/chat/sessions-zep-fail', (req, res, ctx) => {
    return res(ctx.json({
      ...mockSession,
      metadata: { zep_user_created: false, zep_error: 'Connection timeout' }
    }));
  }),

  // Production environment validation
  rest.post('https://api.mental-model.com/api/chat/sessions', (req, res, ctx) => {
    return res(ctx.json(mockSession));
  })
];

// Setup MSW server
export const server = setupServer(...handlers);

// Helper functions for tests
export const setupMockAuth = (user = mockUser) => {
  // Mock the supabase client methods (for the actual auth.getUser implementation)
  mockSupabaseClient.auth.getSession.mockResolvedValue({ 
    data: { session: { user } }, 
    error: null 
  });
  mockSupabaseClient.auth.getUser.mockResolvedValue({ data: { user }, error: null });
  
  // Mock the auth export methods (which call the supabase client)
  mockAuth.getUser.mockResolvedValue(user);
  mockAuth.getSession.mockResolvedValue({ user });
  
  // Mock the chat createSession method to return successful response
  mockChat.createSession.mockResolvedValue({
    data: mockSession,
    error: null
  });
};

export const setupMockAuthFailure = () => {
  // Mock the supabase client methods to return no user
  mockSupabaseClient.auth.getSession.mockResolvedValue({ 
    data: { session: null }, 
    error: null 
  });
  mockSupabaseClient.auth.getUser.mockResolvedValue({ data: { user: null }, error: null });
  
  // Mock the auth export methods to return no user
  mockAuth.getUser.mockResolvedValue(null);
  mockAuth.getSession.mockResolvedValue(null);
  
  // Mock the chat createSession to throw authentication error
  mockChat.createSession.mockRejectedValue(new Error('User not authenticated'));
};

export const createFetchMock = (response, ok = true, status = 200) => {
  return jest.fn(() => 
    Promise.resolve({
      ok,
      status,
      json: () => Promise.resolve(response),
      text: () => Promise.resolve(JSON.stringify(response))
    })
  );
};

// Environment helpers
export const setProductionEnv = () => {
  const originalEnv = process.env.NODE_ENV;
  process.env.NODE_ENV = 'production';
  process.env.REACT_APP_API_URL = 'https://api.mental-model.com';
  return () => {
    process.env.NODE_ENV = originalEnv;
    process.env.REACT_APP_API_URL = 'http://localhost:8000';
  };
};

export const setDevelopmentEnv = () => {
  const originalEnv = process.env.NODE_ENV;
  process.env.NODE_ENV = 'development';
  process.env.REACT_APP_API_URL = 'http://localhost:8000';
  return () => {
    process.env.NODE_ENV = originalEnv;
  };
};