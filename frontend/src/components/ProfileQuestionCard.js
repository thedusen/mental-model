import React, { useState, useEffect } from 'react';
import './ProfileQuestionCard.css';

const ProfileQuestionCard = ({ 
  question, 
  onAnswer, 
  onSkip, 
  currentAnswer = '',
  isLoading = false,
  questionNumber,
  totalQuestions,
  isFirst = false
}) => {
  const [answer, setAnswer] = useState(currentAnswer);
  const [isValid, setIsValid] = useState(false);

  useEffect(() => {
    setAnswer(currentAnswer);
  }, [currentAnswer]);

  useEffect(() => {
    // Validate answer based on question type
    if (question.answer_type === 'text') {
      setIsValid(answer.trim().length > 0);
    } else if (question.answer_type === 'select') {
      setIsValid(answer !== '');
    } else if (question.answer_type === 'scale') {
      setIsValid(answer !== '');
    } else {
      setIsValid(answer !== '');
    }
  }, [answer, question.answer_type]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (isValid && !isLoading) {
      onAnswer(answer);
    }
  };

  const handleSkip = () => {
    if (!isLoading) {
      onSkip();
    }
  };

  const renderInput = () => {
    switch (question.answer_type) {
      case 'text':
        return (
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Type your answer here..."
            className="profile-question-textarea"
            rows={3}
            disabled={isLoading}
            aria-label={`Answer for: ${question.question_text}`}
          />
        );

      case 'select':
        let options = [];
        try {
          // Check if options is already an array (parsed) or a string (needs parsing)
          if (Array.isArray(question.options)) {
            options = question.options;
          } else if (typeof question.options === 'string') {
            options = JSON.parse(question.options || '[]');
          } else {
            options = question.options ? [question.options] : [];
          }
        } catch (error) {
          console.error('Error parsing select options for question', question.id, error);
          options = [];
        }
        return (
          <div className="profile-question-select-group">
            {options.map((option, index) => (
              <label key={index} className="profile-question-option">
                <input
                  type="radio"
                  name={`question-${question.id}`}
                  value={option}
                  checked={answer === option}
                  onChange={(e) => setAnswer(e.target.value)}
                  disabled={isLoading}
                />
                <span className="option-text">{option}</span>
              </label>
            ))}
          </div>
        );

      case 'scale':
        let scaleOptions = {};
        try {
          // Check if options is already an object (parsed) or a string (needs parsing)
          if (typeof question.options === 'object' && question.options !== null) {
            scaleOptions = question.options;
          } else if (typeof question.options === 'string') {
            scaleOptions = JSON.parse(question.options || '{}');
          } else {
            scaleOptions = {};
          }
        } catch (error) {
          console.error('Error parsing scale options for question', question.id, error);
          scaleOptions = {};
        }
        const { min = 1, max = 5, labels = [] } = scaleOptions;
        return (
          <div className="profile-question-scale">
            <div className="scale-options">
              {Array.from({ length: max - min + 1 }, (_, i) => {
                const value = min + i;
                return (
                  <label key={value} className="scale-option">
                    <input
                      type="radio"
                      name={`question-${question.id}`}
                      value={value}
                      checked={answer === value.toString()}
                      onChange={(e) => setAnswer(e.target.value)}
                      disabled={isLoading}
                    />
                    <span className="scale-number">{value}</span>
                    {labels[i] && <span className="scale-label">{labels[i]}</span>}
                  </label>
                );
              })}
            </div>
          </div>
        );

      default:
        return (
          <input
            type="text"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Type your answer..."
            className="profile-question-input"
            disabled={isLoading}
            aria-label={`Answer for: ${question.question_text}`}
          />
        );
    }
  };

  return (
    <div 
      className={`profile-question-card ${isFirst ? 'first-question' : ''}`}
      role="form"
      aria-labelledby={`question-${question.id}-title`}
    >

      <div className="profile-question-content">
        <h3 
          id={`question-${question.id}-title`}
          className="question-title"
        >
          {question.question_text}
        </h3>

        <form onSubmit={handleSubmit} className="question-form">
          {renderInput()}

          <div className="question-actions">
            <button
              type="button"
              onClick={handleSkip}
              className="skip-button"
              disabled={isLoading}
              aria-label="Skip this question"
            >
              Skip for now
            </button>
            <button
              type="submit"
              className={`submit-button ${isValid ? 'valid' : 'invalid'}`}
              disabled={!isValid || isLoading}
              aria-label={isValid ? 'Submit answer' : 'Please provide an answer to continue'}
            >
              {isLoading ? (
                <span className="loading-spinner" aria-hidden="true" />
              ) : (
                questionNumber === totalQuestions ? 'Complete Profile' : 'Next Question'
              )}
            </button>
          </div>
        </form>
      </div>

      {isFirst && (
        <div className="first-question-notice">
          <p>
            🚀 Let's build your business profile to get personalized insights! 
            This takes about 3 minutes and helps me understand your specific challenges.
          </p>
        </div>
      )}
    </div>
  );
};

export default ProfileQuestionCard;