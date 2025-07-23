import React, { useState, useEffect } from 'react';
import { auth, chat } from '../utils/supabase';
import './ChatHistory.css';

const ChatHistory = ({ onSessionSelect, currentSessionId, sidebarMode = false }) => {
  const [sessions, setSessions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [user, setUser] = useState(null);

  // Get current user on component mount and listen for auth changes
  useEffect(() => {
    const getCurrentUser = async () => {
      try {
        console.log('🔍 ChatHistory getCurrentUser starting...');
        const currentUser = await auth.getUser();
        console.log('🔍 ChatHistory getCurrentUser result:', currentUser);
        setUser(currentUser);
        
        if (currentUser) {
          console.log('✅ ChatHistory found user, loading sessions...');
          await loadSessions(currentUser);
        } else {
          console.log('❌ ChatHistory no user found, setting loading false');
          setIsLoading(false);
        }
      } catch (err) {
        console.error('❌ ChatHistory error getting user:', err);
        setError('Failed to get user information');
        setIsLoading(false);
      }
    };
    
    // Listen for auth state changes to catch when user signs in
    const { data: { subscription } } = auth.onAuthStateChange(async (event, session) => {
      console.log('🔍 ChatHistory auth state change:', event, session?.user);
      if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
        setUser(session?.user);
        if (session?.user) {
          await loadSessions(session.user);
        }
      } else if (event === 'SIGNED_OUT') {
        setUser(null);
        setSessions([]);
      }
    });
    
    getCurrentUser();
    
    // Cleanup subscription
    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const loadSessions = async (userToCheck = null) => {
    const currentUser = userToCheck || user;
    console.log('🔍 loadSessions called - user:', currentUser);
    if (!currentUser) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      console.log('📞 Calling chat.getSessions()...');
      const { data, error: sessionError } = await chat.getSessions();
      console.log('📊 getSessions result:', { data, error: sessionError });
      
      if (sessionError) {
        throw sessionError;
      }
      
      console.log('✅ Setting sessions:', data || []);
      setSessions(data || []);
    } catch (err) {
      console.error('❌ Error loading sessions:', err);
      setError('Failed to load chat history');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSessionClick = async (session) => {
    try {
      const { data: messages, error: messagesError } = await chat.getMessages(session.id);
      
      if (messagesError) {
        throw messagesError;
      }
      
      onSessionSelect(session, messages || []);
      setIsExpanded(false); // Collapse after selection
    } catch (err) {
      console.error('Error loading session messages:', err);
      setError('Failed to load session messages');
    }
  };

  const handleDeleteSession = async (session, event) => {
    event.stopPropagation(); // Prevent session selection
    
    if (!window.confirm(`Delete "${session.title || 'Untitled conversation'}"?`)) {
      return;
    }
    
    try {
      const { error: deleteError } = await chat.deleteSession(session.id);
      
      if (deleteError) {
        throw deleteError;
      }
      
      // Refresh sessions list
      await loadSessions();
      
      // If this was the current session, clear it
      if (currentSessionId === session.id) {
        onSessionSelect(null, []);
      }
    } catch (err) {
      console.error('Error deleting session:', err);
      setError('Failed to delete session');
    }
  };

  const createNewSession = async () => {
    if (!user) return;
    
    try {
      const { data: newSession, error: createError } = await chat.createSession();
      
      if (createError) {
        throw createError;
      }
      
      // Select the new session
      onSessionSelect(newSession, []);
      
      // Refresh sessions list to include the new one
      await loadSessions();
    } catch (err) {
      console.error('Error creating session:', err);
      setError('Failed to create new session');
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (diffDays === 1) {
      return 'Yesterday';
    } else if (diffDays < 7) {
      return `${diffDays} days ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  const truncateTitle = (title) => {
    if (!title) return 'Untitled conversation';
    return title.length > 50 ? `${title.substring(0, 47)}...` : title;
  };

  // Hide component entirely while loading or if no user (but show loading in sidebar mode)
  if (!user && !sidebarMode) {
    return null;
  }

  // Sidebar mode always shows content (no expand/collapse)
  if (sidebarMode) {
    return (
      <div className="chat-history sidebar-mode">
        {!user ? (
          <div className="guest-state">
            <p className="guest-message">Sign in to save chat history</p>
          </div>
        ) : (
          <>
            {error && (
              <div className="error-message" role="alert">
                {error}
                <button onClick={loadSessions} className="retry-button">
                  Retry
                </button>
              </div>
            )}

            {isLoading ? (
              <div className="loading-message">Loading history...</div>
            ) : sessions.length === 0 ? (
              <div className="empty-state">
                <p>No conversations yet.</p>
                <p>Start chatting to build your history!</p>
              </div>
            ) : (
              <div className="sessions-list">
                {sessions.map((session) => (
                  <div 
                    key={session.id}
                    className={`session-item ${currentSessionId === session.id ? 'active' : ''}`}
                    onClick={() => handleSessionClick(session)}
                    role="button"
                    tabIndex={0}
                    aria-label={`Load conversation: ${session.title || 'Untitled'}`}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        handleSessionClick(session);
                      }
                    }}
                  >
                    <div className="session-content">
                      <div className="session-title">
                        {truncateTitle(session.title)}
                      </div>
                      <div className="session-meta">
                        <span className="session-date">
                          {formatDate(session.updated_at)}
                        </span>
                      </div>
                    </div>
                    
                    <button
                      className="delete-button"
                      onClick={(e) => handleDeleteSession(session, e)}
                      aria-label={`Delete conversation: ${session.title || 'Untitled'}`}
                      title="Delete conversation"
                    >
                      🗑️
                    </button>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    );
  }

  // Original dropdown mode for compatibility
  if (isLoading || !user) {
    return null;
  }

  return (
    <div className={`chat-history ${isExpanded ? 'expanded' : ''}`}>
      <div className="chat-history-header">
        <button 
          className="expand-button"
          onClick={() => setIsExpanded(!isExpanded)}
          aria-label={isExpanded ? 'Collapse chat history' : 'Expand chat history'}
        >
          📜 History
        </button>
        
        {isExpanded && (
          <button 
            className="new-session-button"
            onClick={createNewSession}
            aria-label="Start new conversation"
          >
            ➕ New
          </button>
        )}
      </div>

      {isExpanded && (
        <div className="chat-history-content">
          {error && (
            <div className="error-message" role="alert">
              {error}
              <button onClick={loadSessions} className="retry-button">
                Retry
              </button>
            </div>
          )}

          {isLoading ? (
            <div className="loading-message">Loading history...</div>
          ) : sessions.length === 0 ? (
            <div className="empty-state">
              <p>No conversations yet.</p>
              <p>Start chatting to build your history!</p>
            </div>
          ) : (
            <div className="sessions-list">
              {sessions.map((session) => (
                <div 
                  key={session.id}
                  className={`session-item ${currentSessionId === session.id ? 'active' : ''}`}
                  onClick={() => handleSessionClick(session)}
                  role="button"
                  tabIndex={0}
                  aria-label={`Load conversation: ${session.title || 'Untitled'}`}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleSessionClick(session);
                    }
                  }}
                >
                  <div className="session-content">
                    <div className="session-title">
                      {truncateTitle(session.title)}
                    </div>
                    <div className="session-meta">
                      <span className="session-date">
                        {formatDate(session.updated_at)}
                      </span>
                    </div>
                  </div>
                  
                  <button
                    className="delete-button"
                    onClick={(e) => handleDeleteSession(session, e)}
                    aria-label={`Delete conversation: ${session.title || 'Untitled'}`}
                    title="Delete conversation"
                  >
                    🗑️
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="history-actions">
            <button 
              onClick={loadSessions}
              className="refresh-button"
              disabled={isLoading}
              aria-label="Refresh chat history"
            >
              🔄 Refresh
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatHistory;