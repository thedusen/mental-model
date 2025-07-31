import React, { useState, useEffect, useRef, useCallback } from 'react';
import { auth, chat } from '../utils/supabase';
import './ChatHistory.css';

const ChatHistory = ({ onSessionSelect, currentSessionId, sidebarMode = false }) => {
  const [sessions, setSessions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [user, setUser] = useState(null);
  const [showRefreshButton, setShowRefreshButton] = useState(false);

  // Debug: Log when user state changes
  useEffect(() => {
    console.log('👤 User state changed:', user);
  }, [user]);
  
  // Search functionality state
  const [isSearchMode, setIsSearchMode] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearchLoading, setIsSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState(null);
  
  // Session editing state
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [originalTitle, setOriginalTitle] = useState('');
  const [isCanceling, setIsCanceling] = useState(false);
  
  // Ref to track if component is mounted to prevent stuck loading
  const isMountedRef = useRef(true);
  
  // Debug: Log when component mounts
  useEffect(() => {
    console.log('🎬 ChatHistory component mounted');
    return () => {
      console.log('🎬 ChatHistory component unmounting');
    };
  }, []);

  // Timer for showing refresh button after loading timeout
  useEffect(() => {
    let timer;
    if (isLoading) {
      setShowRefreshButton(false);
      timer = setTimeout(() => {
        if (isLoading) {
          setShowRefreshButton(true);
        }
      }, 5000); // Show refresh button after 5 seconds of loading
    } else {
      setShowRefreshButton(false);
    }

    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [isLoading]);

  // Memoized loadSessions function to prevent recreation on every render
  const loadSessions = useCallback(async (userToCheck = null, isRetry = false) => {
    const currentUser = userToCheck || user;
    console.log('🔍 loadSessions called - user:', currentUser, 'isRetry:', isRetry);
    if (!currentUser) {
      setIsLoading(false);
      return;
    }
    
    setIsLoading(true);
    setError(null);
    setShowRefreshButton(false); // Restore proper state management
    
    try {
      console.log('📞 Calling chat.getSessions()...');
      
      // Add timeout to prevent infinite loading with better error handling
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error('Request timeout - please check your internet connection')), 10000);
      });
      
      const sessionPromise = chat.getSessions();
      const result = await Promise.race([sessionPromise, timeoutPromise]);
      
      console.log('📊 getSessions result:', result);
      
      // Handle different result formats
      let data, sessionError;
      if (result && typeof result === 'object') {
        if ('data' in result && 'error' in result) {
          // Standard Supabase response format
          data = result.data;
          sessionError = result.error;
        } else if (Array.isArray(result)) {
          // Direct array response
          data = result;
          sessionError = null;
        } else {
          // Unknown format
          console.warn('⚠️ Unexpected response format:', result);
          data = [];
          sessionError = null;
        }
      } else {
        data = [];
        sessionError = null;
      }
      
      if (sessionError) {
        console.error('❌ Session error from Supabase:', sessionError);
        throw new Error(sessionError.message || 'Failed to load sessions');
      }
      
      console.log('✅ Setting sessions:', data || []);
      
      // Always set sessions - React state management is safe
      setSessions(data || []);
      console.log('✅ Sessions set successfully, about to set isLoading to false');
    } catch (err) {
      console.error('❌ Error loading sessions:', err);
      
      // Only update state if component is still mounted
      if (isMountedRef.current) {
        // More specific error handling with better user messaging
        let errorMessage = 'Failed to load chat history';
        let shouldShowRetry = true;
        
        if (err.message && err.message.includes('JWT')) {
          errorMessage = 'Authentication expired - please sign in again';
          shouldShowRetry = false;
        } else if (err.message && err.message.includes('network')) {
          errorMessage = 'Network error - please check your internet connection and try again';
        } else if (err.message && err.message.includes('timeout')) {
          errorMessage = 'Connection timeout - the server is taking too long to respond';
        } else if (err.message && err.message.includes('CORS')) {
          errorMessage = 'Server connection issue - please try refreshing the page';
        } else if (err.message && err.message.includes('500')) {
          errorMessage = 'Server error - please try again in a moment';
        } else if (err.message) {
          errorMessage = `Connection failed: ${err.message}`;
        }
        
        setError(errorMessage);
        
        // Set empty sessions on error to prevent infinite loading
        setSessions([]);
        
        // Show refresh button for recoverable errors
        if (shouldShowRetry) {
          setShowRefreshButton(true);
        }
      }
    } finally {
      console.log('🏁 Finally block reached - isMountedRef.current:', isMountedRef.current);
      // Always set loading to false - React state updates are safe
      console.log('🏁 Setting isLoading to false');
      setIsLoading(false);
    }
  }, [user]); // Dependencies: user state

  // Get current user on component mount and listen for auth changes
  useEffect(() => {
    console.log('🚀 ChatHistory useEffect triggered - Initial setup starting');
    
    const getCurrentUser = async () => {
      try {
        console.log('🔍 ChatHistory getCurrentUser starting...');
        console.log('🔍 ChatHistory mounted status:', isMountedRef.current);
        
        const currentUser = await auth.getUser();
        console.log('🔍 ChatHistory getCurrentUser result:', currentUser);
        console.log('🔍 User exists check:', !!currentUser);
        console.log('🔍 User ID:', currentUser?.id);
        
        console.log('🔍 About to check mounted status...');
        console.log('🔍 isMountedRef.current:', isMountedRef.current);
        
        // Always try to set the user state - the component re-rendering is normal
        console.log('✅ Setting user state to:', currentUser);
        setUser(currentUser);
        
        if (currentUser) {
          console.log('✅ ChatHistory found user, calling loadSessions...');
          // Always call loadSessions - React state management is safe
          await loadSessions(currentUser);
          console.log('✅ ChatHistory loadSessions completed');
        } else {
          console.log('❌ ChatHistory no user found, setting loading false');
          setIsLoading(false);
        }
      } catch (err) {
        console.error('❌ ChatHistory error getting user:', err);
        console.error('❌ Full error details:', err);
        if (isMountedRef.current) {
          setError('Failed to get user information');
          setIsLoading(false);
        }
      }
    };
    
    // Listen for auth state changes to catch when user signs in
    const { data: { subscription } } = auth.onAuthStateChange(async (event, session) => {
      console.log('🔍 ChatHistory auth state change:', event, session?.user);
      if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED' || event === 'INITIAL_SESSION') {
        console.log('🔑 Auth event - setting user and loading sessions');
        // Always set user state for auth events
        setUser(session?.user);
        if (session?.user) {
          await loadSessions(session.user);
        }
      } else if (event === 'SIGNED_OUT') {
        console.log('🚪 User signed out - clearing data');
        setUser(null);
        setSessions([]);
      }
    });
    
    getCurrentUser();
    
    // Cleanup subscription
    return () => {
      subscription.unsubscribe();
      isMountedRef.current = false;
    };
  }, []);

  // Handle page visibility changes to refresh data when user returns
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden && user) {
        // User returned to the page and we have a user - refresh sessions
        console.log('🔄 Page became visible, refreshing sessions...');
        loadSessions();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [user, loadSessions]); // Fixed: removed isLoading to prevent infinite loops

  const handleSessionClick = async (session) => {
    try {
      console.log('🎯 handleSessionClick called for session:', session.id);
      const { data: messages, error: messagesError } = await chat.getMessages(session.id);
      
      if (messagesError) {
        throw messagesError;
      }
      
      console.log('🎯 handleSessionClick retrieved messages:', messages?.length, 'messages');
      console.log('🎯 Message data structure:', messages?.map(m => ({ id: m.id, role: m.role, hasId: !!m.id })));
      
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

  // Search functionality
  const handleSearch = async (query) => {
    if (!user || !query || query.trim().length < 2) {
      return;
    }

    setIsSearchLoading(true);
    setSearchError(null);

    try {
      const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const response = await fetch(
        `${API_URL}/api/chat/search?user_id=${encodeURIComponent(user.id)}&q=${encodeURIComponent(query.trim())}&limit=20`
      );

      if (!response.ok) {
        throw new Error(`Search failed: ${response.status}`);
      }

      const data = await response.json();
      setSearchResults(data.results || []);
    } catch (err) {
      console.error('Search error:', err);
      setSearchError('Failed to search messages');
      setSearchResults([]);
    } finally {
      setIsSearchLoading(false);
    }
  };

  const handleSearchInputChange = (e) => {
    const query = e.target.value;
    setSearchQuery(query);
    
    // Debounce search
    if (query.trim().length >= 2) {
      setTimeout(() => {
        if (query === searchQuery) { // Only search if query hasn't changed
          handleSearch(query);
        }
      }, 300);
    } else {
      setSearchResults([]);
    }
  };

  const handleSearchModeToggle = () => {
    setIsSearchMode(!isSearchMode);
    if (isSearchMode) {
      // Exiting search mode - clear search state
      setSearchQuery('');
      setSearchResults([]);
      setSearchError(null);
    }
  };

  const handleSearchResultClick = async (result) => {
    try {
      // Find the session this message belongs to
      const sessionId = result.chat_sessions?.id || result.session_id;
      if (!sessionId) {
        console.error('No session ID found for search result');
        return;
      }

      // Load the session and its messages
      const { data: messages, error: messagesError } = await chat.getMessages(sessionId);
      
      if (messagesError) {
        throw messagesError;
      }

      // Find the session data
      const session = sessions.find(s => s.id === sessionId) || {
        id: sessionId,
        title: result.chat_sessions?.title || 'Search Result Session',
        updated_at: result.timestamp
      };

      // Select the session
      onSessionSelect(session, messages || []);
      
      // Exit search mode
      setIsSearchMode(false);
      setSearchQuery('');
      setSearchResults([]);
      
    } catch (err) {
      console.error('Error loading search result session:', err);
      setSearchError('Failed to load conversation');
    }
  };

  // Session editing functionality
  const startEditingSession = (session, event) => {
    event.stopPropagation(); // Prevent session selection
    setEditingSessionId(session.id);
    const currentTitle = session.title || '';
    setEditingTitle(currentTitle);
    setOriginalTitle(currentTitle); // Store original title for cancel functionality
  };

  const saveSessionTitle = async (sessionId) => {
    const trimmedTitle = editingTitle.trim();
    if (!trimmedTitle) {
      setError('Session title cannot be empty');
      return;
    }

    try {
      const { error: updateError } = await chat.updateSession(sessionId, { 
        title: trimmedTitle 
      });
      
      if (updateError) {
        throw updateError;
      }
      
      // Refresh sessions to show updated title
      await loadSessions();
      
      // Exit edit mode
      setEditingSessionId(null);
      setEditingTitle('');
      setOriginalTitle(''); // Clear original title storage
      setIsCanceling(false); // Reset canceling flag
      
    } catch (err) {
      console.error('Error updating session title:', err);
      setError('Failed to update session title');
    }
  };

  const cancelEditingSession = () => {
    setIsCanceling(true);
    
    // Immediately restore the original title to prevent any saving
    setEditingTitle(originalTitle);
    
    // Exit edit mode
    setEditingSessionId(null);
    setEditingTitle('');
    setOriginalTitle(''); // Clear original title storage
    
    // Reset canceling flag after a longer delay to ensure onBlur doesn't interfere
    setTimeout(() => {
      setIsCanceling(false);
    }, 200);
  };

  const handleEditKeyPress = (e, sessionId) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      saveSessionTitle(sessionId);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      cancelEditingSession();
    }
  };

  // Hide component entirely while loading or if no user (but show loading in sidebar mode)
  if (!user && !sidebarMode) {
    return null;
  }

  // Sidebar mode always shows content (no expand/collapse)
  if (sidebarMode) {
    console.log('🎯 Rendering sidebar mode - user:', user, 'isLoading:', isLoading, 'sessions.length:', sessions.length);
    return (
      <div className="chat-history sidebar-mode">
        {!user ? (
          <div className="guest-state">
            <p className="guest-message">Sign in to save chat history</p>
            <div style={{ fontSize: '10px', color: '#999', marginTop: '5px' }}>
              Debug: user={user ? 'exists' : 'null'}, isLoading={isLoading ? 'true' : 'false'}
            </div>
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

            {/* Search Interface */}
            <div className="chat-search-section">
              <div className="search-header">
                <button 
                  className={`search-toggle ${isSearchMode ? 'active' : ''}`}
                  onClick={handleSearchModeToggle}
                  aria-label={isSearchMode ? 'Exit search mode' : 'Search conversations'}
                >
                  {isSearchMode ? '🔍 Searching...' : '🔍 Search'}
                </button>
              </div>
              
              {isSearchMode && (
                <div className="search-interface">
                  <input
                    type="text"
                    className="search-input"
                    placeholder="Search your conversations..."
                    value={searchQuery}
                    onChange={handleSearchInputChange}
                    autoFocus
                  />
                  
                  {searchError && (
                    <div className="search-error" role="alert">
                      {searchError}
                    </div>
                  )}
                  
                  {isSearchLoading && (
                    <div className="search-loading">Searching...</div>
                  )}
                  
                  {searchResults.length > 0 && (
                    <div className="search-results">
                      <div className="search-results-header">
                        Found {searchResults.length} message{searchResults.length !== 1 ? 's' : ''}
                      </div>
                      {searchResults.map((result, index) => (
                        <div 
                          key={`${result.session_id}-${index}`}
                          className="search-result-item"
                          onClick={() => handleSearchResultClick(result)}
                          role="button"
                          tabIndex={0}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              handleSearchResultClick(result);
                            }
                          }}
                        >
                          <div className="search-result-content">
                            {result.content.length > 100 
                              ? `${result.content.substring(0, 100)}...` 
                              : result.content}
                          </div>
                          <div className="search-result-meta">
                            <span className="search-result-session">
                              {result.chat_sessions?.title || 'Untitled conversation'}
                            </span>
                            <span className="search-result-role">
                              {result.role === 'user' ? 'You' : 'Assistant'}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {searchQuery.length >= 2 && !isSearchLoading && searchResults.length === 0 && (
                    <div className="no-search-results">
                      No messages found for "{searchQuery}"
                    </div>
                  )}
                </div>
              )}
            </div>

            {isLoading ? (
              <div className="loading-message">
                Loading conversations...
                {showRefreshButton && (
                  <button 
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setShowRefreshButton(false);
                      setError(null);
                      loadSessions(null, true);
                    }} 
                    className="loading-refresh-button"
                    style={{ marginTop: '30px', display: 'block', margin: '30px auto 0' }}
                    type="button"
                  >
                    ↻ Refresh
                  </button>
                )}
              </div>
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
                    className={`session-item ${currentSessionId === session.id ? 'active' : ''} ${editingSessionId === session.id ? 'editing' : ''}`}
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
                        {editingSessionId === session.id ? (
                          <input
                            type="text"
                            className="session-title-input"
                            value={editingTitle}
                            onChange={(e) => {
                              setEditingTitle(e.target.value);
                            }}
                            onKeyDown={(e) => {
                              e.stopPropagation(); // Prevent session click on any key press
                              handleEditKeyPress(e, session.id);
                            }}
                            onKeyPress={(e) => {
                              e.stopPropagation(); // Prevent session click on key press (especially space)
                            }}
                            onBlur={() => {
                              // Add a small delay to allow cancel button to set the flag
                              setTimeout(() => {
                                // Don't save if we're in the process of canceling
                                if (isCanceling) return;
                                
                                // Only save if the title has actually changed
                                if (editingTitle !== originalTitle) {
                                  saveSessionTitle(session.id);
                                } else {
                                  cancelEditingSession();
                                }
                              }, 100);
                            }}
                            autoFocus
                            onClick={(e) => e.stopPropagation()}
                          />
                        ) : (
                          <span 
                            onDoubleClick={(e) => startEditingSession(session, e)}
                            title={`${session.title || 'Untitled conversation'} (Double-click to edit)`}
                          >
                            {truncateTitle(session.title)}
                          </span>
                        )}
                      </div>
                      <div className="session-meta">
                        <span className="session-date">
                          {formatDate(session.updated_at)}
                        </span>
                      </div>
                    </div>
                    
                    <div className="session-actions">
                      {editingSessionId === session.id ? (
                        <>
                          <button
                            className="save-button"
                            onClick={(e) => {
                              e.stopPropagation();
                              saveSessionTitle(session.id);
                            }}
                            aria-label="Save title"
                            title="Save title"
                          >
                            ✓
                          </button>
                          <button
                            className="cancel-button"
                            onMouseDown={(e) => {
                              e.preventDefault(); // Prevent input from losing focus
                              e.stopPropagation();
                            }}
                            onClick={(e) => {
                              e.stopPropagation();
                              e.preventDefault();
                              cancelEditingSession();
                            }}
                            aria-label="Cancel editing"
                            title="Cancel editing"
                          >
                            ✕
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            className="edit-button"
                            onClick={(e) => startEditingSession(session, e)}
                            aria-label={`Edit conversation title: ${session.title || 'Untitled'}`}
                            title="Edit title"
                          >
                            ✎
                          </button>
                          <button
                            className="delete-button"
                            onClick={(e) => handleDeleteSession(session, e)}
                            aria-label={`Delete conversation: ${session.title || 'Untitled'}`}
                            title="Delete conversation"
                          >
                            ×
                          </button>
                        </>
                      )}
                    </div>
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
            <div className="loading-message">
              Loading conversations...
              {showRefreshButton && (
                <button 
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setShowRefreshButton(false);
                    setError(null);
                    loadSessions();
                  }} 
                  className="loading-refresh-button"
                  style={{ marginTop: '30px', display: 'block', margin: '30px auto 0' }}
                  type="button"
                >
                  ↻ Refresh
                </button>
              )}
            </div>
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
                  className={`session-item ${currentSessionId === session.id ? 'active' : ''} ${editingSessionId === session.id ? 'editing' : ''}`}
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
                      {editingSessionId === session.id ? (
                        <input
                          type="text"
                          className="session-title-input"
                          value={editingTitle}
                          onChange={(e) => {
                            setEditingTitle(e.target.value);
                          }}
                          onKeyDown={(e) => {
                            e.stopPropagation(); // Prevent session click on any key press
                            handleEditKeyPress(e, session.id);
                          }}
                          onKeyPress={(e) => {
                            e.stopPropagation(); // Prevent session click on key press (especially space)
                          }}
                          onBlur={() => {
                            // Add a small delay to allow cancel button to set the flag
                            setTimeout(() => {
                              // Don't save if we're in the process of canceling
                              if (isCanceling) return;
                              
                              // Only save if the title has actually changed
                              if (editingTitle !== originalTitle) {
                                saveSessionTitle(session.id);
                              } else {
                                cancelEditingSession();
                              }
                            }, 100);
                          }}
                          autoFocus
                          onClick={(e) => e.stopPropagation()}
                        />
                      ) : (
                        <span 
                          onDoubleClick={(e) => startEditingSession(session, e)}
                          title={`${session.title || 'Untitled conversation'} (Double-click to edit)`}
                        >
                          {truncateTitle(session.title)}
                        </span>
                      )}
                    </div>
                    <div className="session-meta">
                      <span className="session-date">
                        {formatDate(session.updated_at)}
                      </span>
                    </div>
                  </div>
                  
                  <div className="session-actions">
                    {editingSessionId === session.id ? (
                      <>
                        <button
                          className="save-button"
                          onClick={(e) => {
                            e.stopPropagation();
                            saveSessionTitle(session.id);
                          }}
                          aria-label="Save title"
                          title="Save title"
                        >
                          ✓
                        </button>
                        <button
                          className="cancel-button"
                          onMouseDown={(e) => {
                            e.preventDefault(); // Prevent input from losing focus
                            e.stopPropagation();
                          }}
                          onClick={(e) => {
                            e.stopPropagation();
                            e.preventDefault();
                            cancelEditingSession();
                          }}
                          aria-label="Cancel editing"
                          title="Cancel editing"
                        >
                          ✕
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          className="edit-button"
                          onClick={(e) => startEditingSession(session, e)}
                          aria-label={`Edit conversation title: ${session.title || 'Untitled'}`}
                          title="Edit title"
                        >
                          ✎
                        </button>
                        <button
                          className="delete-button"
                          onClick={(e) => handleDeleteSession(session, e)}
                          aria-label={`Delete conversation: ${session.title || 'Untitled'}`}
                          title="Delete conversation"
                        >
                          ×
                        </button>
                      </>
                    )}
                  </div>
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