import React, { useEffect } from 'react';
import { supabase, auth } from '../utils/supabase';

const AuthCallback = () => {
  useEffect(() => {
    const handleAuthCallback = async () => {
      try {
        console.log('🔄 Processing OAuth callback...');
        
        // First, try to get the session from the URL/localStorage
        const { data, error } = await supabase.auth.getSession();
        
        if (error) {
          console.error('❌ Auth callback error:', error);
          // Redirect to home with error
          window.location.href = '/?auth=error';
          return;
        }

        if (data.session) {
          console.log('✅ OAuth session found:', {
            email: data.session.user.email,
            provider: data.session.user.app_metadata?.provider,
            confirmed: data.session.user.email_confirmed_at ? 'yes' : 'no'
          });
          
          // Ensure the user data is complete and properly stored
          const user = data.session.user;
          if (user && user.email) {
            console.log('✅ User data complete, redirecting with success');
            // Add a small delay to ensure session is fully established
            setTimeout(() => {
              window.location.href = '/?auth=success';
            }, 500);
          } else {
            console.error('⚠️ User data incomplete:', user);
            window.location.href = '/?auth=error';
          }
        } else {
          console.log('ℹ️ No session found in callback, checking for hash/params...');
          
          // Try to handle the callback explicitly in case getSession didn't work
          const urlParams = new URLSearchParams(window.location.search);
          const hashParams = new URLSearchParams(window.location.hash.substring(1));
          
          console.log('URL params:', Object.fromEntries(urlParams));
          console.log('Hash params:', Object.fromEntries(hashParams));
          
          if (hashParams.get('access_token') || urlParams.get('code')) {
            console.log('🔄 Found auth tokens in URL, waiting for session...');
            // Wait a bit longer for the session to be established
            setTimeout(async () => {
              try {
                const { data: retryData } = await supabase.auth.getSession();
                if (retryData.session) {
                  console.log('✅ Session established on retry');
                  window.location.href = '/?auth=success';
                } else {
                  console.log('❌ Session still not found after retry');
                  window.location.href = '/?auth=error';
                }
              } catch (retryError) {
                console.error('❌ Retry failed:', retryError);
                window.location.href = '/?auth=error';
              }
            }, 1000);
          } else {
            // No session and no tokens, just redirect home
            console.log('ℹ️ No session or tokens found, redirecting home');
            window.location.href = '/';
          }
        }
      } catch (error) {
        console.error('❌ Error handling auth callback:', error);
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