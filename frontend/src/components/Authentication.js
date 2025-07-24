import React, { useState } from 'react';
import { auth } from '../utils/supabase';
import './Authentication.css';

const Authentication = ({ onAuthSuccess, onClose, mode = 'modal' }) => {
  const [isSignUp, setIsSignUp] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [isClosing, setIsClosing] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    // Basic validation
    if (!email || !password) {
      setError('Email and password are required');
      setIsLoading(false);
      return;
    }

    if (isSignUp && password !== confirmPassword) {
      setError('Passwords do not match');
      setIsLoading(false);
      return;
    }

    if (isSignUp && password.length < 6) {
      setError('Password must be at least 6 characters long');
      setIsLoading(false);
      return;
    }

    try {
      let result;
      
      if (isSignUp) {
        result = await auth.signUp(email, password, { 
          full_name: fullName 
        });
        
        if (result.error) {
          throw result.error;
        }
        
        if (result.data?.user && !result.data.user.email_confirmed_at) {
          setError('Please check your email and click the confirmation link before signing in.');
          setIsSignUp(false); // Switch to sign in mode
        } else {
          onAuthSuccess(result.data.user);
        }
      } else {
        result = await auth.signIn(email, password);
        
        if (result.error) {
          throw result.error;
        }
        
        onAuthSuccess(result.data.user);
      }
    } catch (err) {
      console.error('Authentication error:', err);
      setError(err.message || 'Authentication failed');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleMode = () => {
    setIsSignUp(!isSignUp);
    setError(null);
    setEmail('');
    setPassword('');
    setConfirmPassword('');
    setFullName('');
  };

  const handleClose = () => {
    setIsClosing(true);
    setTimeout(() => {
      onClose();
    }, 300); // Match animation duration
  };

  const handleGoogleSignIn = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const { data, error } = await auth.signInWithGoogle();
      
      if (error) {
        throw error;
      }

      // Google OAuth will redirect to callback page
      // The callback will handle the final authentication
      
    } catch (err) {
      console.error('Google sign in error:', err);
      setError(err.message || 'Google sign in failed');
      setIsLoading(false);
    }
  };

  const isSlideMode = mode === 'slide';
  
  return (
    <div className={`auth-overlay ${isSlideMode ? 'slide-mode' : 'modal-mode'} ${isClosing ? 'closing' : ''}`} onClick={handleClose}>
      <div className={`auth-container ${isSlideMode ? 'auth-slide-panel' : 'auth-modal'} ${isClosing ? 'closing' : ''}`} 
           role="dialog" 
           aria-labelledby="auth-title" 
           aria-modal="true"
           onClick={(e) => e.stopPropagation()}>
        <div className="auth-header">
          <h2 id="auth-title">
            {isSignUp ? 'Create Account' : 'Sign In'}
          </h2>
          <button 
            className="close-button"
            onClick={handleClose}
            aria-label="Close authentication dialog"
          >
            {isSlideMode ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6 6 18M6 6l12 12"/>
              </svg>
            ) : (
              '✕'
            )}
          </button>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {error && (
            <div className="error-message" role="alert">
              {error}
            </div>
          )}

          {isSignUp && (
            <div className="form-group">
              <label htmlFor="full-name">Full Name (optional)</label>
              <input
                id="full-name"
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Enter your full name"
                disabled={isLoading}
              />
            </div>
          )}

          <div className="form-group">
            <label htmlFor="email">Email *</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
              required
              disabled={isLoading}
              autoComplete={isSignUp ? 'email' : 'username'}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password *</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              required
              disabled={isLoading}
              autoComplete={isSignUp ? 'new-password' : 'current-password'}
              minLength={6}
            />
          </div>

          {isSignUp && (
            <div className="form-group">
              <label htmlFor="confirm-password">Confirm Password *</label>
              <input
                id="confirm-password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm your password"
                required
                disabled={isLoading}
                autoComplete="new-password"
                minLength={6}
              />
            </div>
          )}

          <button
            type="submit"
            className="auth-button"
            disabled={isLoading}
          >
            {isLoading ? 'Processing...' : (isSignUp ? 'Create Account' : 'Sign In')}
          </button>

          <div className="auth-divider">
            <span>or</span>
          </div>

          <button
            type="button"
            onClick={handleGoogleSignIn}
            className="google-auth-button"
            disabled={isLoading}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continue with Google
          </button>

          <div className="auth-toggle">
            <p>
              {isSignUp ? 'Already have an account?' : "Don't have an account?"}{' '}
              <button
                type="button"
                onClick={toggleMode}
                className="toggle-button"
                disabled={isLoading}
              >
                {isSignUp ? 'Sign In' : 'Sign Up'}
              </button>
            </p>
          </div>
        </form>

        {isSignUp && (
          <div className="auth-info">
            <h3>Why create an account?</h3>
            <p className="info-description">
              Get the most out of your conversations with the Profit Architect mental model.
            </p>
            <ul>
              <li>💬 Save and access your conversation history</li>
              <li>🔄 Resume conversations across sessions</li>
              <li>🔍 Search through your past interactions</li>
              <li>⚙️ Personalize your experience with Dan's insights</li>
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default Authentication;