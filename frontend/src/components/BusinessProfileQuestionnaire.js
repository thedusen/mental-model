import React, { useState, useEffect, useCallback } from 'react';
import ProfileQuestionCard from './ProfileQuestionCard';
import ProfileProgressIndicator from './ProfileProgressIndicator';
import './BusinessProfileQuestionnaire.css';

const BusinessProfileQuestionnaire = ({ 
  user, 
  onComplete, 
  onProgress,
  onClose,
  initialQuestion = 1,
  mode = 'inline' // 'inline' or 'modal'
}) => {
  const [questions, setQuestions] = useState([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(initialQuestion - 1);
  const [answers, setAnswers] = useState({});
  const [progress, setProgress] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);
  const [isInitialized, setIsInitialized] = useState(false);

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  // Load questions and existing progress
  useEffect(() => {
    const initializeQuestionnaire = async () => {
      if (!user) return;
      
      setIsLoading(true);
      try {
        // Load questions and existing answers in parallel
        const [questionsResponse, progressResponse] = await Promise.all([
          fetch(`${API_URL}/api/business-profile/questions`),
          fetch(`${API_URL}/api/business-profile/progress/${user.id}`, {
            headers: {
              'Authorization': `Bearer ${user.access_token}`,
            },
          })
        ]);

        if (!questionsResponse.ok) {
          throw new Error('Failed to load questions');
        }

        const questionsData = await questionsResponse.json();
        setQuestions(questionsData.questions || []);

        // Load existing progress if available
        if (progressResponse.ok) {
          const progressData = await progressResponse.json();
          setProgress(progressData.progress);
          
          // Set existing answers
          const existingAnswers = {};
          progressData.answers?.forEach(answer => {
            existingAnswers[answer.question_id] = answer.answer;
          });
          setAnswers(existingAnswers);

          // Set current question based on progress
          const nextUnanswered = questionsData.questions?.findIndex(q => 
            !existingAnswers[q.id]
          );
          if (nextUnanswered !== -1) {
            setCurrentQuestionIndex(nextUnanswered);
          }
        }

        setIsInitialized(true);
      } catch (err) {
        console.error('Error initializing questionnaire:', err);
        setError('Failed to load questionnaire. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };

    initializeQuestionnaire();
  }, [user, API_URL]);

  // Save answer to backend
  const saveAnswer = useCallback(async (questionId, answer) => {
    if (!user) return false;

    try {
      const response = await fetch(`${API_URL}/api/business-profile/answer`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.access_token}`,
        },
        body: JSON.stringify({
          user_id: user.id,
          question_id: questionId,
          answer: answer,
          answered_at: new Date().toISOString(),
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to save answer');
      }

      const data = await response.json();
      
      // Update progress if provided
      if (data.progress) {
        setProgress(data.progress);
        onProgress?.(data.progress);
      }

      return true;
    } catch (err) {
      console.error('Error saving answer:', err);
      return false;
    }
  }, [user, API_URL, onProgress]);

  // Handle answer submission
  const handleAnswer = async (answer) => {
    const currentQuestion = questions[currentQuestionIndex];
    if (!currentQuestion) return;

    setIsSaving(true);
    setError(null);

    // Update local state immediately for better UX
    const newAnswers = { ...answers, [currentQuestion.id]: answer };
    setAnswers(newAnswers);

    // Save to backend
    const saved = await saveAnswer(currentQuestion.id, answer);
    
    if (saved) {
      // Move to next question or complete
      if (currentQuestionIndex < questions.length - 1) {
        setCurrentQuestionIndex(currentQuestionIndex + 1);
      } else {
        // Questionnaire completed
        const completedProgress = {
          ...progress,
          completed_at: new Date().toISOString(),
          questions_completed: questions.length,
        };
        setProgress(completedProgress);
        onComplete?.(newAnswers, completedProgress);
      }
    } else {
      setError('Failed to save your answer. Please try again.');
      // Revert local state on error
      setAnswers(answers);
    }

    setIsSaving(false);
  };

  // Handle skip question
  const handleSkip = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
    } else {
      // If skipping the last question, still mark as "complete" with partial data
      onComplete?.(answers, progress);
    }
  };

  // Handle navigation to previous question
  const handlePrevious = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1);
    }
  };

  // Calculate completion percentage
  const completionPercentage = questions.length > 0 
    ? Math.round((Object.keys(answers).length / questions.length) * 100)
    : 0;

  if (isLoading && !isInitialized) {
    return (
      <div className="profile-questionnaire-loading">
        <div className="loading-spinner large" />
        <p>Loading your business profile questionnaire...</p>
      </div>
    );
  }

  if (error && !isInitialized) {
    return (
      <div className="profile-questionnaire-error">
        <div className="error-icon">⚠️</div>
        <p>{error}</p>
        <button 
          onClick={() => window.location.reload()} 
          className="retry-button"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (!questions.length) {
    return (
      <div className="profile-questionnaire-empty">
        <p>No questions available at this time.</p>
      </div>
    );
  }

  const currentQuestion = questions[currentQuestionIndex];
  const isComplete = Object.keys(answers).length === questions.length;

  if (isComplete && progress?.completed_at) {
    return (
      <div className="profile-questionnaire-complete">
        <div className="completion-icon">🎉</div>
        <h3>Profile Complete!</h3>
        <p>
          Thank you for completing your business profile. I now have a much better 
          understanding of your business and can provide more personalized insights 
          and recommendations.
        </p>
        <div className="completion-stats">
          <div className="stat">
            <span className="stat-number">{questions.length}</span>
            <span className="stat-label">Questions Answered</span>
          </div>
          <div className="stat">
            <span className="stat-number">100%</span>
            <span className="stat-label">Profile Complete</span>
          </div>
        </div>
        {mode === 'modal' && (
          <button onClick={onClose} className="close-button">
            Continue Chatting
          </button>
        )}
      </div>
    );
  }

  return (
    <div className={`business-profile-questionnaire ${mode}`}>
      {mode === 'modal' && (
        <div className="questionnaire-header">
          <h2>Build Your Business Profile</h2>
          <button 
            onClick={onClose} 
            className="close-button"
            aria-label="Close questionnaire"
          >
            ✕
          </button>
        </div>
      )}

      <ProfileProgressIndicator 
        current={Object.keys(answers).length}
        total={questions.length}
        percentage={completionPercentage}
      />

      {error && (
        <div className="error-banner" role="alert">
          <span className="error-icon">⚠️</span>
          {error}
          <button 
            onClick={() => setError(null)} 
            className="dismiss-error"
            aria-label="Dismiss error"
          >
            ✕
          </button>
        </div>
      )}

      <ProfileQuestionCard
        question={currentQuestion}
        onAnswer={handleAnswer}
        onSkip={handleSkip}
        currentAnswer={answers[currentQuestion.id] || ''}
        isLoading={isSaving}
        questionNumber={currentQuestionIndex + 1}
        totalQuestions={questions.length}
        isFirst={currentQuestionIndex === 0}
      />

      <div className="questionnaire-navigation">
        {currentQuestionIndex > 0 && (
          <button 
            onClick={handlePrevious}
            className="nav-button previous"
            disabled={isSaving}
          >
            ← Previous Question
          </button>
        )}
        

        {mode === 'modal' && (
          <button 
            onClick={onClose}
            className="nav-button pause"
            disabled={isSaving}
          >
            Pause & Continue Later
          </button>
        )}
      </div>
    </div>
  );
};

export default BusinessProfileQuestionnaire;