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
  variant = 'default', // 'default', 'compact', 'prominent'
  isVisible = true,
  canDismiss = true
}) => {
  const [isDismissed, setIsDismissed] = useState(false);
  const [isAnimatingOut, setIsAnimatingOut] = useState(false);

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

  const handleCTAClick = () => {
    if (userType === 'guest') {
      onOpenAuth?.();
    } else {
      onStartQuestionnaire?.();
    }
  };

  const getNudgeContent = () => {
    switch (userType) {
      case 'guest':
        return {
          icon: '🚀',
          title: 'Get Personalized Business Insights',
          message: 'Sign up to build your business profile and receive tailored advice specific to your challenges and goals.',
          ctaText: 'Sign Up Free',
          ctaClass: 'cta-primary'
        };

      case 'not_started':
        return {
          icon: '💡',
          title: 'Get Better Answers Tailored to Your Business',
          message: 'Complete your 3-minute business profile to receive personalized insights and recommendations.',
          ctaText: 'Start Profile',
          ctaClass: 'cta-primary'
        };

      case 'in_progress':
        const questionsLeft = progress ? (progress.total_questions - progress.questions_completed) : 0;
        return {
          icon: '⏳',
          title: `You Have ${questionsLeft} Questions Left`,
          message: 'Complete your profile to unlock personalized business insights and recommendations.',
          ctaText: 'Continue Profile',
          ctaClass: 'cta-secondary'
        };

      case 'completed':
        return {
          icon: '✅',
          title: 'Profile Complete!',
          message: 'Your business profile is helping me provide more personalized insights.',
          ctaText: 'Update Profile',
          ctaClass: 'cta-subtle'
        };

      default:
        return {
          icon: '🎯',
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
          <span className="nudge-icon">{content.icon}</span>
          <span className="nudge-message-compact">{content.message}</span>
          <button 
            onClick={handleCTAClick}
            className={`nudge-cta compact ${content.ctaClass}`}
            aria-label={content.ctaText}
          >
            {content.ctaText}
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
            <div className="nudge-icon-large">{content.icon}</div>
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
          
          {userType === 'in_progress' && progress && (
            <div className="progress-section">
              <ProfileProgressIndicator
                current={progress.questions_completed}
                total={progress.total_questions}
                variant="compact"
                size="small"
              />
            </div>
          )}
          
          <div className="nudge-actions">
            <button 
              onClick={handleCTAClick}
              className={`nudge-cta prominent ${content.ctaClass}`}
            >
              {content.ctaText}
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

  // Default variant
  return (
    <div className={`profile-nudge-banner default ${userType} ${isAnimatingOut ? 'animating-out' : ''}`}>
      <div className="nudge-content">
        <div className="nudge-main">
          <span className="nudge-icon">{content.icon}</span>
          <div className="nudge-text">
            <h4 className="nudge-title">{content.title}</h4>
            <p className="nudge-message">{content.message}</p>
          </div>
        </div>
        
        {userType === 'in_progress' && progress && (
          <div className="progress-section">
            <ProfileProgressIndicator
              current={progress.questions_completed}
              total={progress.total_questions}
              variant="compact"
              size="small"
              showLabels={false}
            />
          </div>
        )}
        
        <div className="nudge-actions">
          <button 
            onClick={handleCTAClick}
            className={`nudge-cta ${content.ctaClass}`}
          >
            {content.ctaText}
          </button>
          {canDismiss && (
            <button 
              onClick={handleDismiss}
              className="dismiss-button"
              aria-label="Dismiss this notification"
            >
              ✕
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProfileNudgeBanner;