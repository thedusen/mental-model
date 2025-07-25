import { createClient } from '@supabase/supabase-js';

// Get Supabase configuration from environment variables with validation
const supabaseUrl = (() => {
  const envUrl = process.env.REACT_APP_SUPABASE_URL;
  console.log('Environment SUPABASE_URL:', envUrl);
  console.log('Current timestamp:', new Date().toISOString());
  
  if (!envUrl || envUrl.trim() === '') {
    console.warn('REACT_APP_SUPABASE_URL not set, using localhost fallback');
    return 'http://localhost:54321';
  }
  
  // Auto-add https:// protocol if missing (common Supabase deployment issue)
  let finalUrl = envUrl.trim();
  if (!finalUrl.startsWith('http://') && !finalUrl.startsWith('https://')) {
    finalUrl = `https://${finalUrl}`;
    console.log('Added https:// protocol to Supabase URL:', finalUrl);
  }
  
  try {
    new URL(finalUrl);
    return finalUrl;
  } catch (error) {
    console.error('Invalid REACT_APP_SUPABASE_URL:', finalUrl, error);
    throw new Error(`Invalid Supabase URL configuration: ${finalUrl}`);
  }
})();

const supabaseAnonKey = process.env.REACT_APP_SUPABASE_ANON_KEY || 
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0';

// Create Supabase client
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true
  }
});

// Auth helper functions
export const auth = {
  // Sign up with email and password
  signUp: async (email, password, metadata = {}) => {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: metadata
      }
    });
    return { data, error };
  },

  // Sign in with email and password
  signIn: async (email, password) => {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password
    });
    return { data, error };
  },

  // Sign out
  signOut: async () => {
    const { error } = await supabase.auth.signOut();
    return { error };
  },

  // Get current user
  getUser: async () => {
    // First check if we have a session
    const { data: { session } } = await supabase.auth.getSession();
    if (session?.user) {
      console.log('🔍 Found user in session:', session.user);
      return session.user;
    }
    
    // Fallback to getUser if no session
    const { data: { user } } = await supabase.auth.getUser();
    console.log('🔍 getUser fallback result:', user);
    return user;
  },

  // Get current session
  getSession: async () => {
    const { data: { session } } = await supabase.auth.getSession();
    return session;
  },

  // Listen to auth state changes
  onAuthStateChange: (callback) => {
    return supabase.auth.onAuthStateChange(callback);
  },

  // Sign in with Google
  signInWithGoogle: async () => {
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`
      }
    });
    return { data, error };
  },

  // Manually refresh auth state (useful after OAuth redirects)
  refreshAuthState: async () => {
    try {
      console.log('🔄 Manually refreshing auth state...');
      
      // First try to refresh the session
      const { data: refreshData, error: refreshError } = await supabase.auth.refreshSession();
      
      if (refreshError) {
        console.log('⚠️ Session refresh failed, trying to get current session:', refreshError.message);
      } else {
        console.log('✅ Session refreshed successfully');
      }
      
      // Get the current session/user
      const { data: { session }, error: sessionError } = await supabase.auth.getSession();
      
      if (sessionError) {
        console.error('❌ Error getting session during refresh:', sessionError);
        return { user: null, error: sessionError };
      }
      
      if (session?.user) {
        console.log('✅ Auth refresh successful, user found:', session.user.email);
        return { user: session.user, error: null };
      } else {
        console.log('ℹ️ No user session found during refresh');
        return { user: null, error: null };
      }
      
    } catch (error) {
      console.error('❌ Error during manual auth refresh:', error);
      return { user: null, error };
    }
  }
};

// Chat operations
export const chat = {
  // Create a new chat session
  createSession: async (title = null) => {
    console.log('🎯 createSession called with title:', title);
    const user = await auth.getUser();
    console.log('🎯 createSession user:', user);
    if (!user) throw new Error('User not authenticated');

    try {
      console.log('🔍 About to call supabase.from...');
      const { data, error } = await supabase
        .from('chat_sessions')
        .insert({ user_id: user.id, title })
        .select()
        .single();

      console.log('🎯 createSession result:', { data, error });
      return { data, error };
    } catch (err) {
      console.error('❌ createSession caught error:', err);
      return { data: null, error: err };
    }
  },

  // Get user's chat sessions
  getSessions: async (limit = 50, offset = 0) => {
    console.log('🎯 getSessions called');
    const user = await auth.getUser();
    console.log('🎯 getSessions user:', user);
    if (!user) throw new Error('User not authenticated');

    const { data, error } = await supabase
      .from('chat_sessions')
      .select('*')
      .eq('user_id', user.id)
      .order('updated_at', { ascending: false })
      .range(offset, offset + limit - 1);

    console.log('🎯 getSessions query result:', { data, error });
    return { data, error };
  },

  // Get messages for a session
  getMessages: async (sessionId, limit = 100) => {
    const { data, error } = await supabase
      .from('chat_messages')
      .select('*')
      .eq('session_id', sessionId)
      .order('timestamp', { ascending: true })
      .limit(limit);

    return { data, error };
  },

  // Add a message to a session via backend API (enables auto-title generation)
  addMessage: async (sessionId, role, content, metadata = {}) => {
    const user = await auth.getUser();
    if (!user) throw new Error('User not authenticated');

    try {
      const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_URL}/api/chat/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          role,
          content,
          metadata,
          user_id: user.id
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return { data, error: null };
    } catch (err) {
      console.error('Error adding message via API:', err);
      return { data: null, error: err };
    }
  },

  // Legacy method for direct Supabase access (if needed)
  addMessageDirect: async (sessionId, role, content, metadata = {}) => {
    const { data, error } = await supabase
      .from('chat_messages')
      .insert({
        session_id: sessionId,
        role,
        content,
        metadata
      })
      .select()
      .single();

    return { data, error };
  },

  // Update session (e.g., title)
  updateSession: async (sessionId, updates) => {
    const { data, error } = await supabase
      .from('chat_sessions')
      .update(updates)
      .eq('id', sessionId)
      .select()
      .single();

    return { data, error };
  },

  // Delete a session
  deleteSession: async (sessionId) => {
    const { error } = await supabase
      .from('chat_sessions')
      .delete()
      .eq('id', sessionId);

    return { error };
  },

  // Search messages
  searchMessages: async (query, limit = 20) => {
    const user = await auth.getUser();
    if (!user) throw new Error('User not authenticated');

    // First get user's sessions
    const { data: sessions } = await supabase
      .from('chat_sessions')
      .select('id')
      .eq('user_id', user.id);

    if (!sessions || sessions.length === 0) return { data: [], error: null };

    const sessionIds = sessions.map(s => s.id);

    // Search messages in user's sessions
    const { data, error } = await supabase
      .from('chat_messages')
      .select('*, chat_sessions(title)')
      .in('session_id', sessionIds)
      .ilike('content', `%${query}%`)
      .limit(limit);

    return { data, error };
  }
};

// User profile operations
export const profile = {
  // Get user profile
  get: async (userId) => {
    const { data, error } = await supabase
      .from('user_profiles')
      .select('*')
      .eq('id', userId)
      .single();

    return { data, error };
  },

  // Update user profile
  update: async (userId, updates) => {
    const { data, error } = await supabase
      .from('user_profiles')
      .update(updates)
      .eq('id', userId)
      .select()
      .single();

    return { data, error };
  }
};