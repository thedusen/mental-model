import React, { useState, useRef, useEffect } from 'react';
import { auth, profile } from '../utils/supabase';
import Authentication from './Authentication';
import BusinessProfileQuestionnaire from './BusinessProfileQuestionnaire';
import './UserProfile.css';

// Profile Settings Modal Component
const ProfileSettingsModal = ({ user, onClose }) => {
  const [fullName, setFullName] = useState(user?.user_metadata?.full_name || '');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleSave = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      // Update user profile in Supabase
      const { error: updateError } = await profile.update(user.id, {
        full_name: fullName.trim()
      });

      if (updateError) {
        throw updateError;
      }

      setSuccess(true);
      setTimeout(() => {
        onClose();
      }, 1500);

    } catch (err) {
      console.error('Error updating profile:', err);
      setError('Failed to update profile. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Profile Settings</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        <form onSubmit={handleSave} className="modal-form">
          {error && (
            <div className="error-message" role="alert">
              {error}
            </div>
          )}

          {success && (
            <div className="success-message" role="alert">
              Profile updated successfully!
            </div>
          )}

          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={user?.email || ''}
              disabled
              className="form-input disabled"
            />
            <small className="form-hint">Email cannot be changed</small>
          </div>

          <div className="form-group">
            <label htmlFor="fullName">Full Name</label>
            <input
              id="fullName"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Enter your full name"
              className="form-input"
              disabled={isLoading}
            />
          </div>

          <div className="modal-actions">
            <button
              type="button"
              onClick={onClose}
              className="button-secondary"
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="button-primary"
              disabled={isLoading}
            >
              {isLoading ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Preferences Modal Component
const PreferencesModal = ({ user, onClose }) => {
  const [preferences, setPreferences] = useState({
    theme: 'auto', // auto, light, dark
    notifications: true,
    autoSave: true,
    searchHistory: true
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  // Load existing preferences
  useEffect(() => {
    const loadPreferences = async () => {
      try {
        const { data: profileData } = await profile.get(user.id);
        if (profileData && profileData.preferences) {
          setPreferences(prev => ({ ...prev, ...profileData.preferences }));
        }
      } catch (err) {
        console.error('Error loading preferences:', err);
      }
    };

    if (user) {
      loadPreferences();
    }
  }, [user]);

  const handlePreferenceChange = (key, value) => {
    setPreferences(prev => ({ ...prev, [key]: value }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      // Save preferences to user profile
      const { error: updateError } = await profile.update(user.id, {
        preferences: preferences
      });

      if (updateError) {
        throw updateError;
      }

      setSuccess(true);
      setTimeout(() => {
        onClose();
      }, 1500);

    } catch (err) {
      console.error('Error saving preferences:', err);
      setError('Failed to save preferences. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Preferences</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        <form onSubmit={handleSave} className="modal-form">
          {error && (
            <div className="error-message" role="alert">
              {error}
            </div>
          )}

          {success && (
            <div className="success-message" role="alert">
              Preferences saved successfully!
            </div>
          )}

          <div className="form-group">
            <label htmlFor="theme">Theme</label>
            <select
              id="theme"
              value={preferences.theme}
              onChange={(e) => handlePreferenceChange('theme', e.target.value)}
              className="form-select"
              disabled={isLoading}
            >
              <option value="auto">Auto (System)</option>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
          </div>

          <div className="form-group checkbox-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={preferences.notifications}
                onChange={(e) => handlePreferenceChange('notifications', e.target.checked)}
                disabled={isLoading}
              />
              <span className="checkbox-text">Enable notifications</span>
            </label>
          </div>

          <div className="form-group checkbox-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={preferences.autoSave}
                onChange={(e) => handlePreferenceChange('autoSave', e.target.checked)}
                disabled={isLoading}
              />
              <span className="checkbox-text">Auto-save conversations</span>
            </label>
          </div>

          <div className="form-group checkbox-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={preferences.searchHistory}
                onChange={(e) => handlePreferenceChange('searchHistory', e.target.checked)}
                disabled={isLoading}
              />
              <span className="checkbox-text">Keep search history</span>
            </label>
          </div>

          <div className="modal-actions">
            <button
              type="button"
              onClick={onClose}
              className="button-secondary"
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="button-primary"
              disabled={isLoading}
            >
              {isLoading ? 'Saving...' : 'Save Preferences'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const UserProfile = ({ user, onAuthTrigger }) => {
  const [showDropdown, setShowDropdown] = useState(false);
  const [showAuth, setShowAuth] = useState(false);
  const [authMode, setAuthMode] = useState('signin');
  const [showProfileSettings, setShowProfileSettings] = useState(false);
  const [showPreferences, setShowPreferences] = useState(false);
  const [showBusinessProfile, setShowBusinessProfile] = useState(false);
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

  // Expose auth trigger to parent component
  useEffect(() => {
    if (onAuthTrigger) {
      // Pass the function reference, don't call it immediately
      onAuthTrigger(() => setShowAuth(true));
    }
  }, [onAuthTrigger]);

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
            onClick={() => {
              setAuthMode('signin');
              setShowAuth(true);
            }}
            aria-label="Sign in to your account"
          >
            Sign In
          </button>
          <button 
            className="sign-up-button"
            onClick={() => {
              setAuthMode('signup');
              setShowAuth(true);
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
            initialMode={authMode}
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
          {/* Email address hidden as requested */}
        </div>
        <div className="dropdown-arrow">
          <span style={{ fontSize: '20px', display: 'inline-block' }}>
            ⋮
          </span>
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
                setShowProfileSettings(true);
              }}
            >
              Profile Settings
            </button>
            <button 
              className="dropdown-item"
              role="menuitem"
              onClick={() => {
                setShowDropdown(false);
                setShowPreferences(true);
              }}
            >
              Preferences
            </button>
            <button 
              className="dropdown-item"
              role="menuitem"
              onClick={() => {
                setShowDropdown(false);
                setShowBusinessProfile(true);
              }}
            >
              Business Profile
            </button>
          </div>
          <div className="dropdown-divider"></div>
          <div className="dropdown-section">
            <button 
              className="dropdown-item danger"
              role="menuitem"
              onClick={handleSignOut}
            >
              Sign Out
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
          initialMode={authMode}
        />
      )}

      {/* Profile Settings Modal */}
      {showProfileSettings && (
        <ProfileSettingsModal 
          user={user}
          onClose={() => setShowProfileSettings(false)}
        />
      )}

      {/* Preferences Modal */}
      {showPreferences && (
        <PreferencesModal 
          user={user}
          onClose={() => setShowPreferences(false)}
        />
      )}

      {/* Business Profile Modal */}
      {showBusinessProfile && (
        <div className="modal-overlay" onClick={() => setShowBusinessProfile(false)}>
          <div onClick={(e) => e.stopPropagation()}>
            <BusinessProfileQuestionnaire
              user={user}
              onComplete={() => setShowBusinessProfile(false)}
              onProgress={() => {}}
              onClose={() => setShowBusinessProfile(false)}
              mode="modal"
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default UserProfile;