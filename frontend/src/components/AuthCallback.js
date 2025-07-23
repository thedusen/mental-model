import React, { useEffect } from 'react';
import { supabase } from '../utils/supabase';

const AuthCallback = () => {
  useEffect(() => {
    const handleAuthCallback = async () => {
      try {
        // Get the session from URL hash
        const { data, error } = await supabase.auth.getSession();
        
        if (error) {
          console.error('Auth callback error:', error);
          // Redirect to home with error
          window.location.href = '/?auth=error';
          return;
        }

        if (data.session) {
          console.log('Google auth successful:', data.session.user);
          // Redirect to home with success
          window.location.href = '/?auth=success';
        } else {
          // No session, redirect to home
          window.location.href = '/';
        }
      } catch (error) {
        console.error('Error handling auth callback:', error);
        window.location.href = '/?auth=error';
      }
    };

    handleAuthCallback();
  }, []);

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100vh',
      flexDirection: 'column',
      gap: '16px',
      fontFamily: 'system-ui, sans-serif'
    }}>
      <div style={{
        width: '40px',
        height: '40px',
        border: '4px solid #f3f3f3',
        borderTop: '4px solid #3498db',
        borderRadius: '50%',
        animation: 'spin 1s linear infinite'
      }}></div>
      <p>Completing sign in...</p>
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default AuthCallback;