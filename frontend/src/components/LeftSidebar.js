import React, { useState, useEffect } from 'react';
import { auth } from '../utils/supabase';
import ChatHistory from './ChatHistory';
import UserProfile from './UserProfile';
import ProfileNudgeBanner from './ProfileNudgeBanner';
import { ChevronLeft, ChevronRight, Plus } from 'lucide-react';
import './LeftSidebar.css';

const LeftSidebar = ({ 
  onSessionSelect, 
  currentSessionId, 
  onNewChat,
  isCollapsed,
  onToggleCollapse,
  onAuthTrigger,
  showSidebarNudge,
  nudgeDismissalData,
  onSidebarNudgeDismiss
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
        console.log('🔍 LeftSidebar initial user:', currentUser);
        setUser(currentUser);
        
        // Listen for auth state changes
        const { data: { subscription } } = auth.onAuthStateChange(async (event, session) => {
          console.log('🔄 LeftSidebar auth state change:', event, session?.user?.email);
          
          if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
            // For OAuth flows, ensure we get the most up-to-date user data
            if (event === 'SIGNED_IN') {
              // Small delay to ensure session is fully established
              setTimeout(async () => {
                try {
                  const refreshedUser = await auth.getUser();
                  console.log('🔄 Refreshed user after sign-in:', refreshedUser);
                  setUser(refreshedUser);
                } catch (error) {
                  console.error('Error refreshing user after sign-in:', error);
                  setUser(session?.user || null);
                }
              }, 200);
            } else {
              setUser(session?.user || null);
            }
          } else if (event === 'SIGNED_OUT') {
            console.log('🚪 User signed out in LeftSidebar');
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

  // Load business profile progress when user changes (needed for sidebar nudge)
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

  // Helper function to determine user type for nudge
  const getNudgeUserType = () => {
    if (!user) return 'guest';
    if (!businessProfileProgress) return 'not_started';
    if (businessProfileProgress.completed_at) return 'completed';
    if (businessProfileProgress.questions_completed > 0) return 'in_progress';
    return 'not_started';
  };

  // Handle sidebar nudge dismissal
  const handleSidebarNudgeDismiss = () => {
    onSidebarNudgeDismiss?.(user);
  };

  // Handle sidebar nudge questionnaire start
  const handleStartQuestionnaire = async (mode = 'chat') => {
    if (!user) {
      onAuthTrigger?.();
      return;
    }
    
    // For authenticated users, focus the main chat area and start questionnaire there
    console.log('Sidebar nudge - focusing chat area for questionnaire start');
    
    // Dismiss the sidebar nudge since they're about to start in the main chat
    handleSidebarNudgeDismiss();
    
    // Focus the main chat textarea
    setTimeout(() => {
      const chatInput = document.querySelector('.chat-panel textarea');
      if (chatInput) {
        chatInput.focus();
        // Trigger questionnaire start by sending a special message
        const event = new CustomEvent('startQuestionnaireFromSidebar', {
          detail: { mode }
        });
        window.dispatchEvent(event);
      }
    }, 100);
  };

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

          {/* Sidebar Nudge Section */}
          {!isCollapsed && showSidebarNudge && !isLoadingAuth && (
            <div className="sidebar-nudge-section">
              <ProfileNudgeBanner
                user={user}
                progress={businessProfileProgress}
                onStartQuestionnaire={handleStartQuestionnaire}
                onDismiss={handleSidebarNudgeDismiss}
                onOpenAuth={onAuthTrigger}
                userType={getNudgeUserType()}
                variant="sidebar"
                isVisible={true}
                canDismiss={true}
                preferredMode="chat"
              />
            </div>
          )}

          {/* User Profile Section - moved to bottom */}
          <div className="user-profile-section">
            {!isLoadingAuth && (
              <UserProfile user={user} onAuthTrigger={onAuthTrigger} />
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