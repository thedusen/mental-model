import React, { useState, useEffect } from 'react';
import { auth } from '../utils/supabase';
import ChatHistory from './ChatHistory';
import UserProfile from './UserProfile';
import ProfileProgressIndicator from './ProfileProgressIndicator';
import { ChevronLeft, ChevronRight, Plus } from 'lucide-react';
import './LeftSidebar.css';

const LeftSidebar = ({ 
  onSessionSelect, 
  currentSessionId, 
  onNewChat,
  isCollapsed,
  onToggleCollapse
}) => {
  const [user, setUser] = useState(null);
  const [isLoadingAuth, setIsLoadingAuth] = useState(true);
  const [businessProfileProgress, setBusinessProfileProgress] = useState(null);
  
  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
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

  // Load business profile progress when user changes
  useEffect(() => {
    const loadBusinessProfileProgress = async () => {
      if (!user) {
        setBusinessProfileProgress(null);
        return;
      }

      try {
        const response = await fetch(`${API_URL}/api/business-profile/progress/${user.id}`);
        if (response.ok) {
          const data = await response.json();
          setBusinessProfileProgress(data.progress);
        }
      } catch (error) {
        console.error('Error loading business profile progress in sidebar:', error);
      }
    };

    loadBusinessProfileProgress();
  }, [user, API_URL]);


  return (
    <aside 
      className={`left-sidebar ${isCollapsed ? 'collapsed' : ''}`}
      role="navigation" 
      aria-label="Chat navigation and history"
    >
      {!isCollapsed && (
        <>
          {/* Sidebar Header with Collapse and New Chat */}
          <div className="sidebar-header">
            <button
              className="sidebar-toggle-with-text"
              onClick={onToggleCollapse}
              aria-label="Collapse sidebar"
              title="Collapse sidebar"
            >
              <ChevronLeft size={20} />
              <span>Collapse</span>
            </button>
            
            <button 
              className="new-chat-button"
              onClick={onNewChat}
              aria-label="Start new conversation"
            >
              <Plus size={16} />
              <span>New Chat</span>
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

          {/* Business Profile Progress Section */}
          {user && businessProfileProgress && (
            <div className="business-profile-section">
              <h3 className="section-title">Business Profile</h3>
              <ProfileProgressIndicator
                current={businessProfileProgress.questions_completed}
                total={businessProfileProgress.total_questions}
                variant="compact"
                size="small"
                showLabels={false}
              />
              <div className="profile-status">
                {businessProfileProgress.completed_at ? (
                  <span className="status-completed">✓ Complete</span>
                ) : (
                  <span className="status-progress">
                    {businessProfileProgress.questions_completed}/{businessProfileProgress.total_questions} questions
                  </span>
                )}
              </div>
            </div>
          )}

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
        <div className="collapsed-sidebar">
          <button
            className="collapsed-menu-button"
            onClick={onToggleCollapse}
            aria-label="Expand sidebar"
            title="Expand sidebar"
          >
            <ChevronRight size={20} />
          </button>
          
          <button
            className="collapsed-new-chat-button"
            onClick={onNewChat}
            aria-label="New chat"
            title="New chat"
          >
            <Plus size={20} />
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