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

// Helper function to ensure Zep user exists after authentication
const ensureZepUserExists = async (userId) => {
  try {
    console.log('🔧 POST-AUTH: Creating Zep user for', userId);
    const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    
    const response = await fetch(`${API_URL}/api/users/ensure-zep-user`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ user_id: userId })
    });
    
    const result = await response.json();
    
    if (result.created) {
      console.log('✅ POST-AUTH: Zep user created successfully for', userId);
    } else {
      console.log('ℹ️ POST-AUTH: Zep user already existed or creation skipped for', userId);
    }
    
    return result;
  } catch (error) {
    console.warn('⚠️ POST-AUTH: Zep user creation failed (non-critical):', error);
    // Don't throw - this is non-critical for auth flow
    return { created: false, error: error.message };
  }
};

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
    
    // Create Zep user after successful signup (non-blocking)
    if (data?.user?.id && !error) {
      ensureZepUserExists(data.user.id).catch(err => 
        console.warn('POST-AUTH: Zep user creation failed for signup:', err)
      );
    }
    
    return { data, error };
  },

  // Sign in with email and password
  signIn: async (email, password) => {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password
    });
    
    // Create Zep user after successful signin (non-blocking)
    if (data?.user?.id && !error) {
      ensureZepUserExists(data.user.id).catch(err => 
        console.warn('POST-AUTH: Zep user creation failed for signin:', err)
      );
    }
    
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
        
        // Create Zep user after successful OAuth callback (non-blocking)
        ensureZepUserExists(session.user.id).catch(err => 
          console.warn('POST-AUTH: Zep user creation failed for OAuth callback:', err)
        );
        
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
    console.log('🔍 SESSION CREATION FLOW STARTED - User ID:', user?.id);
    console.log('🎯 createSession user:', user);
    if (!user) throw new Error('User not authenticated');

    try {
      // 🔧 FIX: Use backend API instead of direct Supabase to ensure Zep user creation
      console.log('🔍 About to call backend API for session creation...');
      console.log('📡 CALLING /api/chat/sessions - This should create Zep user');
      
      // Environment validation to prevent production failures
      const API_URL = (() => {
        const url = process.env.REACT_APP_API_URL;
        if (!url && process.env.NODE_ENV === 'production') {
          throw new Error('REACT_APP_API_URL must be configured in production');
        }
        return url || 'http://localhost:8000';
      })();
      
      const response = await fetch(`${API_URL}/api/chat/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: user.id,
          title: title
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
      }

      const data = await response.json();
      console.log('🎯 createSession result from backend:', data);
      console.log('✅ SESSION CREATION SUCCESS - Zep user should be created now');
      console.log('📝 Session ID:', data.id, 'User ID:', data.user_id);
      
      // Convert backend response to match expected format
      return { 
        data: {
          id: data.id,
          user_id: data.user_id,
          title: data.title,
          created_at: data.created_at,
          updated_at: data.updated_at,
          metadata: data.metadata || {}
        }, 
        error: null 
      };
    } catch (err) {
      console.error('❌ SESSION CREATION FAILED:', err);
      console.error('❌ This means Zep user was NOT created');
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