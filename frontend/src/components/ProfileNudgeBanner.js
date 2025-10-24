import React, { useState, useEffect } from 'react';
import ProfileProgressIndicator from './ProfileProgressIndicator';
import './ProfileNudgeBanner.css';

const ProfileNudgeBanner = ({ 
  user,
  progress,
  onStartQuestionnaire,
  onDismiss,
  onOpenAuth,
  userType = 'guest', // 'guest', 'not_started', 'in_progress', 'completed'
  variant = 'default', // 'default', 'compact', 'prominent', 'sidebar'
  isVisible = true,
  canDismiss = true,
  preferredMode = 'chat' // 'chat' or 'modal'
}) => {
  const [isDismissed, setIsDismissed] = useState(false);
  const [isAnimatingOut, setIsAnimatingOut] = useState(false);
  const [isLoading, setIsLoading] = useState(false);


  // Don't show if explicitly not visible or dismissed
  if (!isVisible || isDismissed) {
    return null;
  }

  const handleDismiss = () => {
    if (!canDismiss) return;
    
    setIsAnimatingOut(true);
    setTimeout(() => {
      setIsDismissed(true);
      onDismiss?.();
    }, 300); // Match CSS animation duration
  };

  const handleCTAClick = async () => {
    
    if (userType === 'guest') {
      onOpenAuth?.();
    } else {
      setIsLoading(true);
      
      try {
        await onStartQuestionnaire?.(preferredMode);
      } catch (error) {
        console.error('Error starting questionnaire:', error);
      } finally {
        // Keep loading state for a moment to show user that action was taken
        setTimeout(() => {
          setIsLoading(false);
        }, 1000);
      }
    }
  };

  const getNudgeContent = () => {
    // Sidebar uses same content as default chat version
    if (variant === 'sidebar') {
      switch (userType) {
        case 'guest':
          return {
            title: 'Get Personalized Business Insights',
            message: 'Sign up to build your business profile and receive tailored advice specific to your challenges and goals.',
            ctaText: 'Sign Up Free',
            ctaClass: 'cta-primary'
          };

        case 'not_started':
          return {
            title: 'Get Better Answers Tailored to Your Business',
            message: preferredMode === 'chat' 
              ? 'I\'ll ask you some quick questions here in chat to understand your business better and provide personalized insights.'
              : 'Complete your 3-minute business profile to receive personalized insights and recommendations.',
            ctaText: preferredMode === 'chat' ? 'Let\'s Chat!' : 'Start Profile',
            ctaClass: 'cta-primary'
          };

        case 'in_progress':
          const questionsLeft = progress ? (progress.total_questions - progress.questions_completed) : 0;
          return {
            title: `You Have ${questionsLeft} Questions Left`,
            message: preferredMode === 'chat'
              ? 'Let\'s continue building your business profile right here in our conversation.'
              : 'Complete your profile to unlock personalized business insights and recommendations.',
            ctaText: preferredMode === 'chat' ? 'Continue in Chat' : 'Continue Profile',
            ctaClass: 'cta-secondary'
          };

        case 'completed':
          return {
            title: 'Profile Complete!',
            message: 'Your business profile is helping me provide more personalized insights.',
            ctaText: 'Update Profile',
            ctaClass: 'cta-subtle'
          };

        default:
          return {
            title: 'Build Your Business Profile',
            message: 'Get personalized insights by telling me about your business.',
            ctaText: 'Get Started',
            ctaClass: 'cta-primary'
          };
      }
    }

    // Default chat content (existing)
    switch (userType) {
      case 'guest':
        return {
          title: 'Get Personalized Business Insights',
          message: 'Sign up to build your business profile and receive tailored advice specific to your challenges and goals.',
          ctaText: 'Sign Up Free',
          ctaClass: 'cta-primary'
        };

      case 'not_started':
        return {
          title: 'Get Better Answers Tailored to Your Business',
          message: preferredMode === 'chat' 
            ? 'I\'ll ask you some quick questions here in chat to understand your business better and provide personalized insights.'
            : 'Complete your 3-minute business profile to receive personalized insights and recommendations.',
          ctaText: preferredMode === 'chat' ? 'Let\'s Chat!' : 'Start Profile',
          ctaClass: 'cta-primary'
        };

      case 'in_progress':
        const questionsLeft = progress ? (progress.total_questions - progress.questions_completed) : 0;
        return {
          title: `You Have ${questionsLeft} Questions Left`,
          message: preferredMode === 'chat'
            ? 'Let\'s continue building your business profile right here in our conversation.'
            : 'Complete your profile to unlock personalized business insights and recommendations.',
          ctaText: preferredMode === 'chat' ? 'Continue in Chat' : 'Continue Profile',
          ctaClass: 'cta-secondary'
        };

      case 'completed':
        return {
          title: 'Profile Complete!',
          message: 'Your business profile is helping me provide more personalized insights.',
          ctaText: 'Update Profile',
          ctaClass: 'cta-subtle'
        };

      default:
        return {
          title: 'Build Your Business Profile',
          message: 'Get personalized insights by telling me about your business.',
          ctaText: 'Get Started',
          ctaClass: 'cta-primary'
        };
    }
  };

  const content = getNudgeContent();

  if (variant === 'compact') {
    return (
      <div className={`profile-nudge-banner compact ${isAnimatingOut ? 'animating-out' : ''}`}>
        <div className="nudge-content-compact">
          {content.icon && <span className="nudge-icon">{content.icon}</span>}
          <span className="nudge-message-compact">{content.message}</span>
          <button 
            onClick={handleCTAClick}
            className={`nudge-cta compact ${content.ctaClass}`}
            aria-label={content.ctaText}
            disabled={isLoading}
          >
            {isLoading ? (
              <span className="loading-spinner-inline" />
            ) : (
              content.ctaText
            )}
          </button>
          {canDismiss && (
            <button 
              onClick={handleDismiss}
              className="dismiss-button compact"
              aria-label="Dismiss"
            >
              ✕
            </button>
          )}
        </div>
      </div>
    );
  }

  if (variant === 'prominent') {
    return (
      <div className={`profile-nudge-banner prominent ${isAnimatingOut ? 'animating-out' : ''}`}>
        <div className="nudge-content-prominent">
          <div className="nudge-header">
            {content.icon && <div className="nudge-icon-large">{content.icon}</div>}
            <div className="nudge-text">
              <h3 className="nudge-title">{content.title}</h3>
              <p className="nudge-message">{content.message}</p>
            </div>
            {canDismiss && (
              <button 
                onClick={handleDismiss}
                className="dismiss-button prominent"
                aria-label="Dismiss"
              >
                ✕
              </button>
            )}
          </div>
          
          <div className="nudge-actions">
            <button 
              onClick={handleCTAClick}
              className={`nudge-cta prominent ${content.ctaClass}`}
              disabled={isLoading}
            >
              {isLoading ? (
                <span className="loading-spinner-inline" />
              ) : (
                content.ctaText
              )}
            </button>
            
            {userType === 'not_started' && (
              <div className="nudge-benefits">
                <span className="benefit-item">💬 Personalized advice</span>
                <span className="benefit-item">🎯 Tailored recommendations</span>
                <span className="benefit-item">⚡ 3-minute setup</span>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (variant === 'sidebar') {
    return (
      <div className={`profile-nudge-banner sidebar ${userType} ${isAnimatingOut ? 'animating-out' : ''}`}>
        <div className="nudge-content-sidebar">
          <div className="nudge-main">
            <div className="nudge-text">
              <h4 className="nudge-title">{content.title}</h4>
              <p className="nudge-message">{content.message}</p>
            </div>
          </div>
          
          <div className="nudge-actions">
            {canDismiss && (
              <button 
                onClick={handleDismiss}
                className="dismiss-text-button sidebar"
                aria-label="Dismiss profile setup reminder"
              >
                Dismiss
              </button>
            )}
            <button 
              onClick={handleCTAClick}
              className={`nudge-cta sidebar ${content.ctaClass}`}
              disabled={isLoading}
              aria-label={content.ctaText}
            >
              {isLoading ? (
                <span className="loading-spinner-inline" />
              ) : (
                content.ctaText
              )}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Default variant
  return (
    <div className={`profile-nudge-banner default ${userType} ${isAnimatingOut ? 'animating-out' : ''}`}>
      {canDismiss && (
        <button 
          onClick={handleDismiss}
          className="dismiss-button"
          aria-label="Dismiss this notification"
        >
          ✕
        </button>
      )}
      <div className="nudge-content">
        <div className="nudge-main">
          {content.icon && <span className="nudge-icon">{content.icon}</span>}
          <div className="nudge-text">
            <h4 className="nudge-title">{content.title}</h4>
            <p className="nudge-message">{content.message}</p>
          </div>
        </div>
        
        <div className="nudge-actions">
          <button 
            onClick={handleCTAClick}
            className={`nudge-cta ${content.ctaClass}`}
            disabled={isLoading}
          >
            {isLoading ? (
              <span className="loading-spinner-inline" />
            ) : (
              content.ctaText
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProfileNudgeBanner;