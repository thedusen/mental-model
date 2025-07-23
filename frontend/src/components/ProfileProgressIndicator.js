import React from 'react';
import './ProfileProgressIndicator.css';

const ProfileProgressIndicator = ({ 
  current, 
  total, 
  percentage, 
  size = 'medium', // 'small', 'medium', 'large'
  showLabels = true,
  showPercentage = true,
  variant = 'default' // 'default', 'compact', 'detailed'
}) => {
  const progress = percentage !== undefined ? percentage : Math.round((current / total) * 100);
  const completedQuestions = current || 0;
  const totalQuestions = total || 0;
  
  const getProgressColor = () => {
    if (progress >= 100) return '#10b981'; // green
    if (progress >= 75) return '#3b82f6'; // blue
    if (progress >= 50) return '#f59e0b'; // amber
    if (progress >= 25) return '#8b5cf6'; // purple
    return '#6b7280'; // gray
  };

  const getProgressMessage = () => {
    if (progress >= 100) return 'Profile Complete! 🎉';
    if (progress >= 75) return 'Almost there!';
    if (progress >= 50) return 'Great progress!';
    if (progress >= 25) return 'Good start!';
    return 'Just getting started';
  };

  if (variant === 'compact') {
    return (
      <div className={`profile-progress-indicator compact ${size}`}>
        <div className="progress-bar-container">
          <div 
            className="progress-bar"
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Profile completion: ${progress}%`}
          >
            <div 
              className="progress-fill"
              style={{ 
                width: `${progress}%`,
                backgroundColor: getProgressColor()
              }}
            />
          </div>
          {showPercentage && (
            <span className="progress-percentage">{progress}%</span>
          )}
        </div>
      </div>
    );
  }

  if (variant === 'detailed') {
    return (
      <div className={`profile-progress-indicator detailed ${size}`}>
        <div className="progress-header">
          <h4 className="progress-title">Business Profile</h4>
          <span className="progress-stats">
            {completedQuestions} of {totalQuestions} questions
          </span>
        </div>
        
        <div className="progress-bar-container">
          <div 
            className="progress-bar"
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Profile completion: ${completedQuestions} of ${totalQuestions} questions answered`}
          >
            <div 
              className="progress-fill"
              style={{ 
                width: `${progress}%`,
                backgroundColor: getProgressColor()
              }}
            />
          </div>
          <div className="progress-labels">
            <span className="progress-message">{getProgressMessage()}</span>
            <span className="progress-percentage">{progress}%</span>
          </div>
        </div>

        {progress < 100 && (
          <div className="progress-encouragement">
            <p>
              {totalQuestions - completedQuestions} questions remaining • 
              Estimated {Math.ceil((totalQuestions - completedQuestions) * 0.5)} minutes
            </p>
          </div>
        )}
      </div>
    );
  }

  // Default variant
  return (
    <div className={`profile-progress-indicator default ${size}`}>
      {showLabels && (
        <div className="progress-labels">
          <span className="progress-text">
            Business Profile Progress
          </span>
          <span className="progress-stats">
            {completedQuestions}/{totalQuestions}
          </span>
        </div>
      )}
      
      <div className="progress-bar-container">
        <div 
          className="progress-bar"
          role="progressbar"
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Profile completion: ${completedQuestions} of ${totalQuestions} questions answered, ${progress}% complete`}
        >
          <div 
            className="progress-fill"
            style={{ 
              width: `${progress}%`,
              backgroundColor: getProgressColor()
            }}
          />
        </div>
        
        {showPercentage && (
          <div className="progress-info">
            <span className="progress-percentage">{progress}%</span>
            <span className="progress-message">{getProgressMessage()}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProfileProgressIndicator;