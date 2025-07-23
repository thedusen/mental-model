import React, { useState, useEffect } from 'react';
import { auth } from '../utils/supabase';
import ChatHistory from './ChatHistory';
import UserProfile from './UserProfile';
import './LeftSidebar.css';

const LeftSidebar = ({ 
  onSessionSelect, 
  currentSessionId, 
  onNewChat,
  isCollapsed,
  onToggleCollapse,
  onHoverChange
}) => {
  const [user, setUser] = useState(null);
  const [isLoadingAuth, setIsLoadingAuth] = useState(true);
  const [isHovering, setIsHovering] = useState(false);

  // Authentication state management
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const currentUser = await auth.getUser();
        setUser(currentUser);
        
        // Listen for auth state changes
        const { data: { subscription } } = auth.onAuthStateChange((event, session) => {
          if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
            setUser(session?.user);
          } else if (event === 'SIGNED_OUT') {
            setUser(null);
          }
        });

        // Cleanup subscription
        return () => subscription.unsubscribe();
      } catch (error) {
        console.error('Error initializing auth in sidebar:', error);
      } finally {
        setIsLoadingAuth(false);
      }
    };

    initializeAuth();
  }, []);

  const handleMouseEnter = () => {
    setIsHovering(true);
    if (onHoverChange) {
      onHoverChange(true);
    }
  };

  const handleMouseLeave = () => {
    setIsHovering(false);
    if (onHoverChange) {
      onHoverChange(false);
    }
  };

  return (
    <aside 
      className={`left-sidebar ${isCollapsed ? 'collapsed' : ''}`}
      role="navigation" 
      aria-label="Chat navigation and history"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {!isCollapsed && (
        <>
          {/* Sidebar Header with New Chat and Toggle */}
          <div className="sidebar-header">
            <button 
              className="new-chat-button"
              onClick={onNewChat}
              aria-label="Start new conversation"
            >
              <svg 
                width="16" 
                height="16" 
                viewBox="0 0 24 24" 
                fill="none" 
                stroke="currentColor" 
                strokeWidth="2"
              >
                <path d="M12 5v14M5 12h14" />
              </svg>
              <span>New Chat</span>
            </button>
            
            <button
              className="sidebar-toggle"
              onClick={onToggleCollapse}
              aria-label="Collapse sidebar"
              title="Collapse sidebar"
            >
              <svg 
                width="16" 
                height="16" 
                viewBox="0 0 24 24" 
                fill="none" 
                stroke="currentColor" 
                strokeWidth="2"
              >
                <path d="M15 18l-6-6 6-6" />
              </svg>
            </button>
          </div>

          {/* Chat History */}
          <div className="chat-history-section">
            {!isLoadingAuth && (
              <ChatHistory 
                onSessionSelect={onSessionSelect}
                currentSessionId={currentSessionId}
                sidebarMode={true}
              />
            )}
          </div>

          {/* User Profile Section - moved to bottom */}
          <div className="user-profile-section">
            {!isLoadingAuth && (
              <UserProfile user={user} />
            )}
          </div>
        </>
      )}

      {/* Collapsed state with icons */}
      {isCollapsed && (
        <div 
          className="collapsed-sidebar"
          onMouseEnter={() => setIsHovering(true)}
          onMouseLeave={() => setIsHovering(false)}
        >
          <button
            className="collapsed-menu-button"
            onClick={onToggleCollapse}
            aria-label="Expand sidebar"
            title="Expand sidebar"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 6h18M3 12h18M3 18h18"/>
            </svg>
          </button>
          
          <button
            className="collapsed-new-chat-button"
            onClick={onNewChat}
            aria-label="New chat"
            title="New chat"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 8v8m-4-4h8"/>
            </svg>
          </button>
          
          <button
            className="collapsed-history-button"
            onClick={onToggleCollapse}
            aria-label="View chat history"
            title="View chat history"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
          </button>
        </div>
      )}
    </aside>
  );
};

export default LeftSidebar;