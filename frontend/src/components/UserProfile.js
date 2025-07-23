import React, { useState, useRef, useEffect } from 'react';
import { auth } from '../utils/supabase';
import Authentication from './Authentication';
import './UserProfile.css';

const UserProfile = ({ user }) => {
  const [showDropdown, setShowDropdown] = useState(false);
  const [showAuth, setShowAuth] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close dropdown on escape key
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setShowDropdown(false);
      }
    };

    if (showDropdown) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [showDropdown]);

  const handleSignOut = async () => {
    try {
      await auth.signOut();
      setShowDropdown(false);
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  const handleAuthSuccess = (user) => {
    setShowAuth(false);
  };

  const getInitials = (email) => {
    if (!email) return '?';
    return email.charAt(0).toUpperCase();
  };

  const getAvatarUrl = (user) => {
    // Check for Google profile picture
    if (user?.user_metadata?.avatar_url) {
      return user.user_metadata.avatar_url;
    }
    // Check for email provider avatar (Gravatar, etc.)
    if (user?.user_metadata?.picture) {
      return user.user_metadata.picture;
    }
    return null;
  };

  if (!user) {
    // Guest state with sign in/up buttons
    return (
      <div className="user-profile guest">
        <div className="auth-buttons">
          <button 
            className="sign-in-button"
            onClick={() => setShowAuth(true)}
            aria-label="Sign in to your account"
          >
            Sign In
          </button>
          <button 
            className="sign-up-button"
            onClick={() => {
              setShowAuth(true);
              // You could set a state to default to sign up mode
            }}
            aria-label="Create new account"
          >
            Sign Up
          </button>
        </div>

        {/* Authentication Modal */}
        {showAuth && (
          <Authentication 
            onAuthSuccess={handleAuthSuccess}
            onClose={() => setShowAuth(false)}
            mode="slide"
          />
        )}
      </div>
    );
  }

  const avatarUrl = getAvatarUrl(user);
  const displayName = user.user_metadata?.full_name || user.email?.split('@')[0] || 'User';

  return (
    <div className="user-profile authenticated" ref={dropdownRef}>
      <button
        className="user-profile-button"
        onClick={() => setShowDropdown(!showDropdown)}
        aria-label="User menu"
        aria-expanded={showDropdown}
        aria-haspopup="true"
      >
        <div className="user-avatar">
          {avatarUrl ? (
            <img 
              src={avatarUrl} 
              alt={`${displayName}'s avatar`}
              onError={(e) => {
                e.target.style.display = 'none';
                e.target.nextSibling.style.display = 'flex';
              }}
            />
          ) : null}
          <div 
            className="avatar-fallback" 
            style={{ display: avatarUrl ? 'none' : 'flex' }}
          >
            {getInitials(user.email)}
          </div>
        </div>
        <div className="user-info">
          <div className="user-name" title={displayName}>
            {displayName}
          </div>
          <div className="user-email" title={user.email}>
            {user.email}
          </div>
        </div>
        <div className="dropdown-arrow">
          <svg 
            width="16" 
            height="16" 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="currentColor" 
            strokeWidth="2"
            style={{ transform: showDropdown ? 'rotate(180deg)' : 'rotate(0deg)' }}
          >
            <path d="M6 9l6 6 6-6"/>
          </svg>
        </div>
      </button>

      {/* Dropdown Menu */}
      {showDropdown && (
        <div 
          className="user-dropdown" 
          role="menu"
          aria-labelledby="user-menu"
        >
          <div className="dropdown-section">
            <button 
              className="dropdown-item"
              role="menuitem"
              onClick={() => {
                setShowDropdown(false);
                // TODO: Open profile settings modal
                console.log('Open profile settings');
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
              <span>Profile Settings</span>
            </button>
            <button 
              className="dropdown-item"
              role="menuitem"
              onClick={() => {
                setShowDropdown(false);
                // TODO: Open preferences modal
                console.log('Open preferences');
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="3"/>
                <path d="M12 1v6m0 6v6m11-7h-6m-6 0H1"/>
              </svg>
              <span>Preferences</span>
            </button>
          </div>
          <div className="dropdown-divider"></div>
          <div className="dropdown-section">
            <button 
              className="dropdown-item danger"
              role="menuitem"
              onClick={handleSignOut}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <polyline points="16,17 21,12 16,7"/>
                <line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
              <span>Sign Out</span>
            </button>
          </div>
        </div>
      )}

      {/* Authentication Modal (for reauthentication if needed) */}
      {showAuth && (
        <Authentication 
          onAuthSuccess={handleAuthSuccess}
          onClose={() => setShowAuth(false)}
          mode="slide"
        />
      )}
    </div>
  );
};

export default UserProfile;