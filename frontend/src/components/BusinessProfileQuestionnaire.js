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
        // Initialize questionnaire and get current question/progress
        const [startResponse, statusResponse] = await Promise.all([
          fetch(`${API_URL}/api/questionnaire/start`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${user.access_token}`,
            },
            body: JSON.stringify({ user_id: user.id })
          }),
          fetch(`${API_URL}/api/questionnaire/status/${user.id}`, {
            headers: {
              'Authorization': `Bearer ${user.access_token}`,
            },
          })
        ]);

        if (!startResponse.ok) {
          throw new Error('Failed to initialize questionnaire');
        }

        const startData = await startResponse.json();
        
        // Get status to understand current progress
        if (statusResponse.ok) {
          const statusData = await statusResponse.json();
          setProgress({
            current: statusData.current_question,
            total: statusData.total_questions,
            status: statusData.status,
            completed_questions: statusData.questions_completed
          });
          
          // If questionnaire is already completed, show completion state
          if (statusData.status === 'completed') {
            setIsInitialized(true);
            setIsLoading(false);
            return;
          }
        }

        // Get current question from start response or fetch current
        let currentQuestionData;
        if (startData.question) {
          currentQuestionData = startData;
        } else {
          const currentResponse = await fetch(`${API_URL}/api/questionnaire/current/${user.id}`, {
            headers: {
              'Authorization': `Bearer ${user.access_token}`,
            },
          });
          if (currentResponse.ok) {
            currentQuestionData = await currentResponse.json();
          }
        }

        if (currentQuestionData?.question) {
          // Create questions array with just the current question for now
          // We'll load others as needed
          setQuestions([currentQuestionData.question]);
          setCurrentQuestionIndex(0);
          
          // Set progress from response
          if (currentQuestionData.progress) {
            setProgress(currentQuestionData.progress);
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

  // Save answer to backend using new questionnaire API
  const saveAnswer = useCallback(async (questionId, answer) => {
    if (!user) return false;

    try {
      const response = await fetch(`${API_URL}/api/questionnaire/answer`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.access_token}`,
        },
        body: JSON.stringify({
          user_id: user.id,
          question_id: questionId,
          answer_text: answer,
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

      // Handle completion or next question
      if (data.completed) {
        return { completed: true, data };
      } else if (data.question) {
        // Update questions array with next question
        setQuestions(prev => {
          const newQuestions = [...prev];
          const nextIndex = newQuestions.length;
          newQuestions[nextIndex] = data.question;
          return newQuestions;
        });
        return { completed: false, data };
      }

      return { completed: false, data };
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
    const result = await saveAnswer(currentQuestion.id, answer);
    
    if (result && result !== false) {
      if (result.completed) {
        // Questionnaire completed
        const completedProgress = {
          ...progress,
          completed_at: new Date().toISOString(),
          status: 'completed',
        };
        setProgress(completedProgress);
        onComplete?.(newAnswers, completedProgress);
      } else if (result.data?.question) {
        // Move to next question
        setCurrentQuestionIndex(currentQuestionIndex + 1);
        if (result.data.progress) {
          setProgress(result.data.progress);
        }
      }
    } else {
      setError('Failed to save your answer. Please try again.');
      // Revert local state on error
      setAnswers(answers);
    }

    setIsSaving(false);
  };

  // Handle skip question using API command
  const handleSkip = async () => {
    if (!user) return;
    
    setIsSaving(true);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/api/questionnaire/command`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.access_token}`,
        },
        body: JSON.stringify({
          user_id: user.id,
          command: 'skip',
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to skip question');
      }

      const data = await response.json();
      
      if (data.completed) {
        // Questionnaire completed
        const completedProgress = {
          ...progress,
          status: 'completed',
        };
        setProgress(completedProgress);
        onComplete?.(answers, completedProgress);
      } else if (data.question) {
        // Move to next question
        setQuestions(prev => {
          const newQuestions = [...prev];
          const nextIndex = newQuestions.length;
          newQuestions[nextIndex] = data.question;
          return newQuestions;
        });
        setCurrentQuestionIndex(currentQuestionIndex + 1);
        if (data.progress) {
          setProgress(data.progress);
        }
      }
    } catch (err) {
      console.error('Error skipping question:', err);
      setError('Failed to skip question. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  // Handle navigation to previous question using API command
  const handlePrevious = async () => {
    if (!user) return;
    
    setIsSaving(true);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/api/questionnaire/command`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.access_token}`,
        },
        body: JSON.stringify({
          user_id: user.id,
          command: 'previous',
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to go to previous question');
      }

      const data = await response.json();
      
      if (data.error) {
        setError(data.error);
      } else if (data.question) {
        // Update to previous question - we may need to rebuild questions array
        setQuestions(prev => {
          const newQuestions = [...prev];
          // Insert previous question at current position - 1
          if (currentQuestionIndex > 0) {
            newQuestions[currentQuestionIndex - 1] = data.question;
          }
          return newQuestions;
        });
        setCurrentQuestionIndex(Math.max(0, currentQuestionIndex - 1));
        if (data.progress) {
          setProgress(data.progress);
        }
      }
    } catch (err) {
      console.error('Error going to previous question:', err);
      setError('Failed to go to previous question. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  // Calculate completion percentage from progress
  const completionPercentage = progress 
    ? Math.round((progress.current / progress.total) * 100)
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
  const isComplete = progress?.status === 'completed';

  if (isComplete) {
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
            <span className="stat-number">{progress?.total || 11}</span>
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
        current={progress?.current || 0}
        total={progress?.total || 11}
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