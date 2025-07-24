import React, { useState, useRef, useEffect, forwardRef, useImperativeHandle } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { auth, chat } from '../utils/supabase';
import Authentication from './Authentication';
import BusinessProfileQuestionnaire from './BusinessProfileQuestionnaire';
import ProfileNudgeBanner from './ProfileNudgeBanner';
import './ChatPanel.css';

const ChatPanel = forwardRef(({ selectedNode, chatContextNode, onClearChatContext, onFullscreenChange, externalInput, onExternalInputReceived, onSessionChange, onOpenSidebarAuth }, ref) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [hasMessagesEver, setHasMessagesEver] = useState(false);
  const textareaRef = useRef(null);

  // Authentication and chat history state
  const [user, setUser] = useState(null);
  const [currentSession, setCurrentSession] = useState(null);
  const [showAuth, setShowAuth] = useState(false);
  const [isLoadingAuth, setIsLoadingAuth] = useState(true);

  // Business profile questionnaire state
  const [showQuestionnaire, setShowQuestionnaire] = useState(false);
  const [businessProfileProgress, setBusinessProfileProgress] = useState(null);
  const [nudgeStatus, setNudgeStatus] = useState(null);
  
  // New chat-integrated questionnaire state
  const [questionnaireActive, setQuestionnaireActive] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [questionnaireProgress, setQuestionnaireProgress] = useState({ current: 0, total: 11 });
  const [tempQuestionnaireMessages, setTempQuestionnaireMessages] = useState([]);
  const [preQuestionnaireState, setPreQuestionnaireState] = useState(null);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when messages change
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Chat-integrated questionnaire functions
  const startChatQuestionnaire = async () => {
    console.log('🎯 startChatQuestionnaire called, user:', user);
    if (!user) {
      console.error('❌ No user found, cannot start questionnaire');
      // Show error message to user
      const errorMessage = {
        id: Date.now(),
        role: 'assistant',
        content: 'Please sign in to start your business profile questionnaire.',
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
      return;
    }
    
    try {
      console.log('📡 Making API request to start questionnaire...');
      setLoading(true);
      const response = await axios.post(`${API_URL}/api/questionnaire/start`, {
        user_id: user.id
      });
      
      console.log('✅ Questionnaire start response:', response.data);
      
      if (response.data.question) {
        console.log('📝 Setting questionnaire active with question:', response.data.question);
        
        // Store current chat state before starting questionnaire
        setPreQuestionnaireState({
          messages: messages.filter(msg => !msg.isQuestionnaire),
          session: currentSession
        });
        
        setQuestionnaireActive(true);
        setCurrentQuestion(response.data.question);
        setQuestionnaireProgress(response.data.progress);
        
        // Add AI question to temporary messages
        const aiMessage = {
          id: Date.now(),
          role: 'assistant',
          content: response.data.message,
          isQuestionnaire: true
        };
        setTempQuestionnaireMessages([aiMessage]);
        setMessages(prev => [...prev, aiMessage]);
        console.log('💬 Added questionnaire message to chat');
      } else {
        console.warn('⚠️ No question found in response');
        // Show error message to user
        const errorMessage = {
          id: Date.now(),
          role: 'assistant', 
          content: 'Sorry, I had trouble loading your business profile questions. Please try again.',
          isError: true
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error('❌ Error starting questionnaire:', error);
      console.error('Error details:', error.response?.data || error.message);
      
      // Show user-friendly error message
      const errorMessage = {
        id: Date.now(),
        role: 'assistant',
        content: 'Sorry, I encountered an error starting your business profile questionnaire. Please try again in a moment.',
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const submitQuestionnaireAnswer = async (answerText) => {
    if (!user || !currentQuestion) return;
    
    try {
      setLoading(true);
      
      // Add user message to temporary messages
      const userMessage = {
        id: Date.now(),
        role: 'user',
        content: answerText,
        isQuestionnaire: true
      };
      setTempQuestionnaireMessages(prev => [...prev, userMessage]);
      setMessages(prev => [...prev, userMessage]);
      
      console.log('🔍 Submitting questionnaire answer:', {
        user_id: user.id,
        question_id: currentQuestion.id,
        answer_text: answerText,
        currentQuestion: currentQuestion
      });
      
      const response = await axios.post(`${API_URL}/api/questionnaire/answer`, {
        user_id: user.id,
        question_id: currentQuestion.id,
        answer_text: answerText
      });
      
      console.log('✅ Questionnaire answer response:', response.data);
      
      if (response.data.completed) {
        // Questionnaire completed
        setQuestionnaireActive(false);
        setCurrentQuestion(null);
        setTempQuestionnaireMessages([]);
        
        // Update business profile progress to reflect completion
        setBusinessProfileProgress({
          status: 'completed',
          current_question: 11,
          total_questions: 11,
          questions_completed: 11,
          should_show_nudge: false
        });
        
        // Update nudge status to reflect completion
        setNudgeStatus({
          user_type: 'completed',
          should_show_nudge: false,
          progress: {
            status: 'completed',
            current_question: 11,
            total_questions: 11
          }
        });
        
        const completionMessage = {
          id: Date.now() + 1,
          role: 'assistant',
          content: response.data.message,
          isQuestionnaire: true
        };
        setMessages(prev => [...prev, completionMessage]);
        
        // Restore previous chat state after showing completion message briefly
        setTimeout(() => {
          if (preQuestionnaireState) {
            // Restore previous messages and session
            setMessages(preQuestionnaireState.messages);
            setCurrentSession(preQuestionnaireState.session);
            console.log('🔄 Restored previous chat state');
          } else {
            // No previous state, start fresh
            setMessages([]);
            setCurrentSession(null);
            console.log('🆕 Started fresh chat after questionnaire');
          }
          setPreQuestionnaireState(null);
        }, 3000); // Show completion message for 3 seconds
        
        // Reload business profile data to ensure nudge state is correct
        setTimeout(async () => {
          try {
            const [progressResponse, nudgeResponse] = await Promise.all([
              fetch(`${API_URL}/api/questionnaire/status/${user.id}`),
              fetch(`${API_URL}/api/business-profile/nudge-status/${user.id}`)
            ]);
            
            if (progressResponse.ok) {
              const progressData = await progressResponse.json();
              setBusinessProfileProgress(progressData);
            }
            
            if (nudgeResponse.ok) {
              const nudgeData = await nudgeResponse.json();
              setNudgeStatus(nudgeData);
            }
          } catch (error) {
            console.error('Error reloading business profile data after completion:', error);
          }
        }, 1000);
        
      } else if (response.data.question) {
        // Next question
        setCurrentQuestion(response.data.question);
        setQuestionnaireProgress(response.data.progress);
        
        const nextQuestionMessage = {
          id: Date.now() + 1,
          role: 'assistant',  
          content: response.data.message,
          isQuestionnaire: true
        };
        setTempQuestionnaireMessages(prev => [...prev, nextQuestionMessage]);
        setMessages(prev => [...prev, nextQuestionMessage]);
      }
    } catch (error) {
      console.error('❌ Error submitting questionnaire answer:', error);
      console.error('❌ Error details:', error.response?.data);
      console.error('❌ Error status:', error.response?.status);
    } finally {
      setLoading(false);
    }
  };

  const handleQuestionnaireCommand = async (command) => {
    if (!user) return;
    
    try {
      setLoading(true);
      const response = await axios.post(`${API_URL}/api/questionnaire/command`, {
        user_id: user.id,
        command: command
      });
      
      if (response.data.paused) {
        // Questionnaire paused
        setQuestionnaireActive(false);
        setCurrentQuestion(null);
        setTempQuestionnaireMessages([]);
        
      } else if (response.data.completed) {
        // Questionnaire completed
        setQuestionnaireActive(false);
        setCurrentQuestion(null);  
        setTempQuestionnaireMessages([]);
        
      } else if (response.data.question) {
        // Continue with next/previous question
        setCurrentQuestion(response.data.question);
        setQuestionnaireProgress(response.data.progress);
      }
      
      // Add response message
      const responseMessage = {
        id: Date.now(),
        role: 'assistant',
        content: response.data.message,
        isQuestionnaire: true
      };
      setMessages(prev => [...prev, responseMessage]);
      
    } catch (error) {
      console.error('Error handling questionnaire command:', error);
    } finally {
      setLoading(false);
    }
  };
  // Nudge dismissal state management
  const [nudgeDismissalData, setNudgeDismissalData] = useState(() => {
    try {
      const stored = localStorage.getItem('nudge-dismissal-data');
      if (stored) {
        return JSON.parse(stored);
      }
      
      // Migration: check for old dismissal key
      const oldDismissed = localStorage.getItem('business-profile-dismissed') === 'true';
      const initialData = {
        guest: { count: oldDismissed ? 1 : 0, lastDismissed: oldDismissed ? Date.now() : null },
        authenticated: { dismissed: false }
      };
      
      // Clean up old key
      if (oldDismissed) {
        localStorage.removeItem('business-profile-dismissed');
        localStorage.setItem('nudge-dismissal-data', JSON.stringify(initialData));
      }
      
      return initialData;
    } catch {
      return {
        guest: { count: 0, lastDismissed: null },
        authenticated: { dismissed: false }
      };
    }
  });

  // Use environment variable for API URL, fallback to localhost for development
  let API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
  
  // Ensure the API URL has a protocol
  if (API_URL && !API_URL.startsWith('http://') && !API_URL.startsWith('https://')) {
    API_URL = `https://${API_URL}`;
  }

  // Expose methods to parent component
  useImperativeHandle(ref, () => ({
    handleSessionSelect: (session, sessionMessages) => {
      setCurrentSession(session);
      if (onSessionChange) {
        onSessionChange(session);
      }
      
      if (sessionMessages && sessionMessages.length > 0) {
        // Convert session messages to the format expected by the chat panel
        const formattedMessages = sessionMessages.map(msg => ({
          id: msg.id,
          role: msg.role,
          content: msg.content,
          context: msg.metadata?.context || []
        }));
        setMessages(formattedMessages);
        setHasMessagesEver(true);
      } else {
        setMessages([]);
      }
    },
    handleNewChat: () => {
      setCurrentSession(null);
      setMessages([]);
      setHasMessagesEver(false);
      if (onSessionChange) {
        onSessionChange(null);
      }
    }
  }));

  useEffect(() => {
    if (textareaRef.current) {
      // Use requestAnimationFrame to coordinate with transitions
      requestAnimationFrame(() => {
        if (textareaRef.current) {
          // Reset height to 'auto' to ensure it shrinks when text is deleted
          textareaRef.current.style.height = 'auto';
          // Set the height to the scroll height to expand with content
          textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
        }
      });
    }
  }, [input]);

  // Track when messages first appear
  useEffect(() => {
    if (messages.length > 0 && !hasMessagesEver) {
      setHasMessagesEver(true);
    }
  }, [messages, hasMessagesEver]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Notify parent component when fullscreen state changes
  useEffect(() => {
    if (onFullscreenChange) {
      onFullscreenChange(isFullscreen);
    }
  }, [isFullscreen, onFullscreenChange]);

  // Handle external input from suggestion buttons
  useEffect(() => {
    if (externalInput && externalInput.trim() !== '') {
      setInput(externalInput);
      if (onExternalInputReceived) {
        onExternalInputReceived();
      }
      // Focus the textarea
      setTimeout(() => {
        if (textareaRef.current) {
          textareaRef.current.focus();
          textareaRef.current.setSelectionRange(textareaRef.current.value.length, textareaRef.current.value.length);
        }
      }, 100);
    }
  }, [externalInput, onExternalInputReceived]);

  // Check authentication status on component mount
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const currentUser = await auth.getUser();
        console.log('🔍 Initial user check:', currentUser);
        setUser(currentUser);
        
        // Listen for auth state changes
        const { data: { subscription } } = auth.onAuthStateChange((event, session) => {
          console.log('🔄 Auth state change:', event, session?.user);
          if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
            setUser(session?.user);
          } else if (event === 'SIGNED_OUT') {
            setUser(null);
            setCurrentSession(null);
            setMessages([]);
          }
        });

        // Cleanup subscription
        return () => subscription.unsubscribe();
      } catch (error) {
        console.error('Error initializing auth:', error);
      } finally {
        setIsLoadingAuth(false);
      }
    };

    initializeAuth();
  }, []);

  // Load business profile data when user logs in
  useEffect(() => {
    const loadBusinessProfileData = async () => {
      if (!user) {
        setBusinessProfileProgress(null);
        setNudgeStatus(null);
        return;
      }

      try {
        console.log('🔍 Loading business profile data for user:', user.id);
        
        // Load questionnaire status and nudge status
        const [progressResponse, nudgeResponse] = await Promise.all([
          fetch(`${API_URL}/api/questionnaire/status/${user.id}`),
          fetch(`${API_URL}/api/business-profile/nudge-status/${user.id}`)
        ]);

        console.log('📊 Progress response status:', progressResponse.status);
        console.log('📊 Nudge response status:', nudgeResponse.status);

        if (progressResponse.ok) {
          const progressData = await progressResponse.json();
          console.log('📊 Progress data:', progressData);
          setBusinessProfileProgress(progressData);
        } else {
          console.error('❌ Progress response not ok:', progressResponse.status, progressResponse.statusText);
          setBusinessProfileProgress(null);
        }

        if (nudgeResponse.ok) {
          const nudgeData = await nudgeResponse.json();
          console.log('📊 Nudge data:', nudgeData);
          setNudgeStatus(nudgeData);
        } else {
          console.error('❌ Nudge response not ok:', nudgeResponse.status, nudgeResponse.statusText);
          // Set default nudge status for new users
          setNudgeStatus({
            user_type: 'not_started',
            should_show_nudge: true,
            progress: null
          });
        }
      } catch (error) {
        console.error('❌ Error loading business profile data:', error);
        // Set fallback status for new users
        setNudgeStatus({
          user_type: 'not_started',
          should_show_nudge: true,
          progress: null
        });
      }
    };

    loadBusinessProfileData();
  }, [user, API_URL]);

  // Reset authenticated dismissal when user logs in (show nudge even if dismissed as guest)
  useEffect(() => {
    if (user && nudgeDismissalData.authenticated.dismissed) {
      const newDismissalData = {
        ...nudgeDismissalData,
        authenticated: { dismissed: false }
      };
      setNudgeDismissalData(newDismissalData);
      localStorage.setItem('nudge-dismissal-data', JSON.stringify(newDismissalData));
    }
  }, [user?.id]); // Only run when user ID changes (login/logout)

  // Save messages to current session when they change
  useEffect(() => {
    const saveMessages = async () => {
      if (!user || !currentSession || messages.length === 0) return;

      try {
        // Get the last two messages (user and assistant)
        const recentMessages = messages.slice(-2);
        
        // Filter out messages that already have IDs (already saved)
        const unsavedMessages = recentMessages.filter(msg => !msg.id);
        
        console.log('💾 Save check - total messages:', messages.length, 'recent:', recentMessages.length, 'unsaved:', unsavedMessages.length);
        console.log('💾 Recent message IDs:', recentMessages.map(m => ({ role: m.role, id: m.id })));
        
        if (unsavedMessages.length === 0) {
          console.log('⏸️ No unsaved messages to save');
          return;
        }
        
        for (const message of unsavedMessages) {
          console.log('💾 Saving message:', message.role, 'content length:', message.content.length);
          const { data: savedMessage } = await chat.addMessage(
            currentSession.id,
            message.role,
            message.content,
            message.context ? { context: message.context } : {}
          );
          
          // Update state immutably instead of mutating the object
          if (savedMessage) {
            setMessages(prevMessages => 
              prevMessages.map(msg => 
                msg === message ? { ...msg, id: savedMessage.id } : msg
              )
            );
          }
        }
      } catch (error) {
        console.error('Error saving messages:', error);
      }
    };

    // Only save if we have new messages and a current session
    if (messages.length > 0 && currentSession && user) {
      console.log('💾 Attempting to save messages:', messages.length, 'messages to session:', currentSession.id);
      saveMessages();
    } else {
      console.log('⏸️ Skipping message save - messages:', messages.length, 'session:', !!currentSession, 'user:', !!user);
    }
  }, [messages, currentSession, user]);


  // Create a new session when user starts typing (if not authenticated, show auth)
  const createNewSessionIfNeeded = async () => {
    console.log('📝 createNewSessionIfNeeded - user:', user, 'currentSession:', currentSession);
    
    if (!user) {
      console.log('❌ No user - showing auth');
      setShowAuth(true);
      return false;
    }

    // Create session if we don't have one (regardless of message count)
    if (!currentSession) {
      try {
        console.log('🆕 Creating new session...');
        const { data: newSession, error } = await chat.createSession();
        console.log('📊 Session creation result:', { data: newSession, error });
        
        if (error) {
          console.error('❌ Session creation error:', error);
          throw error;
        }
        
        if (!newSession) {
          console.error('❌ No session returned from chat.createSession');
          return false;
        }
        
        console.log('✅ New session created:', newSession.id);
        setCurrentSession(newSession);
        return true;
      } catch (error) {
        console.error('❌ Error creating session:', error);
        return false;
      }
    }
    console.log('✅ Session already exists:', currentSession.id);
    return true;
  };

  // Business profile questionnaire handlers
  const handleQuestionnaireComplete = (answers, progress) => {
    console.log('Questionnaire completed:', { answers, progress });
    setBusinessProfileProgress(progress);
    setShowQuestionnaire(false);
    
    // Update nudge status to reflect completion
    setNudgeStatus({
      user_type: 'completed',
      should_show_nudge: false,
      progress: progress
    });
  };

  const handleQuestionnaireProgress = (progress) => {
    console.log('Questionnaire progress updated:', progress);
    setBusinessProfileProgress(progress);
    
    // Update nudge status
    setNudgeStatus({
      user_type: 'in_progress',
      should_show_nudge: true,
      progress: progress
    });
  };

  const handleStartQuestionnaire = async (mode = 'chat') => {
    console.log('🚀 handleStartQuestionnaire called with mode:', mode, 'user:', user);
    console.log('🔍 Current businessProfileProgress:', businessProfileProgress);
    
    if (mode === 'modal') {
      setShowQuestionnaire(true);
      return;
    } 
    
    if (mode === 'chat') {
      console.log('📋 Starting chat-integrated questionnaire...');
      
      // Check if we need to resume or start fresh
      if (businessProfileProgress && businessProfileProgress.status === 'in_progress') {
        console.log('🔄 Resuming existing questionnaire...');
        try {
          const success = await createNewSessionIfNeeded();
          console.log('🔗 Session creation result for resume:', success);
          if (success) {
            await resumeQuestionnaire();
          } else {
            console.error('❌ Failed to create session for resume');
            // Show error message to user
            const errorMessage = {
              id: Date.now(),
              role: 'assistant',
              content: 'I had trouble setting up the chat session. Please try refreshing the page and clicking "Continue in Chat" again.',
              isError: true
            };
            setMessages(prev => [...prev, errorMessage]);
          }
        } catch (error) {
          console.error('❌ Session creation promise rejected:', error);
          const errorMessage = {
            id: Date.now(),
            role: 'assistant',
            content: 'I had trouble setting up the chat session. Please try refreshing the page and clicking "Continue in Chat" again.',
            isError: true
          };
          setMessages(prev => [...prev, errorMessage]);
        }
      } else {
        console.log('🎯 Starting new questionnaire...');
        console.log('🎯 businessProfileProgress status:', businessProfileProgress?.status);
        // Start the new chat-integrated questionnaire
        try {
          const success = await createNewSessionIfNeeded();
          console.log('🔗 Session creation result:', success);
          if (success) {
            console.log('🎯 About to call startChatQuestionnaire...');
            await startChatQuestionnaire();
          } else {
            console.error('❌ Failed to create session, cannot start questionnaire');
            // Show error message to user
            const errorMessage = {
              id: Date.now(),
              role: 'assistant',
              content: 'I had trouble setting up the chat session. Please try refreshing the page and clicking "Let\'s Chat!" again.',
              isError: true
            };
            setMessages(prev => [...prev, errorMessage]);
          }
        } catch (error) {
          console.error('❌ Session creation promise rejected:', error);
          const errorMessage = {
            id: Date.now(),
            role: 'assistant',
            content: 'I had trouble setting up the chat session. Please try refreshing the page and clicking "Let\'s Chat!" again.',
            isError: true
          };
          setMessages(prev => [...prev, errorMessage]);
        }
      }
    }
  };

  const resumeQuestionnaire = async () => {
    if (!user) return;
    
    try {
      setLoading(true);
      console.log('🔄 Resuming questionnaire...');
      
      // Get current question
      const response = await axios.get(`${API_URL}/api/questionnaire/current/${user.id}`);
      console.log('📋 Current question response:', response.data);
      
      if (response.data.question) {
        setQuestionnaireActive(true);
        setCurrentQuestion(response.data.question);
        setQuestionnaireProgress(response.data.progress);
        
        // Add AI message to show current question
        const aiMessage = {
          id: Date.now(),
          role: 'assistant',
          content: `Resuming your business profile. ${response.data.question.question_text}`,
          isQuestionnaire: true
        };
        setTempQuestionnaireMessages([aiMessage]);
        setMessages(prev => [...prev, aiMessage]);
      }
    } catch (error) {
      console.error('❌ Error resuming questionnaire:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleNudgeDismiss = async () => {
    const now = Date.now();
    let newDismissalData;
    
    if (user) {
      // Authenticated user dismissal - only dismiss until they complete profile
      newDismissalData = {
        ...nudgeDismissalData,
        authenticated: { dismissed: true, lastDismissed: now }
      };
      
      // Record dismissal on backend
      try {
        await fetch(`${API_URL}/api/business-profile/nudge-dismissed`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ user_id: user.id }),
        });
      } catch (error) {
        console.error('Error recording nudge dismissal:', error);
      }
    } else {
      // Guest user dismissal - track count and implement 3-strike rule
      const newCount = nudgeDismissalData.guest.count + 1;
      newDismissalData = {
        ...nudgeDismissalData,
        guest: { 
          count: newCount, 
          lastDismissed: now 
        }
      };
    }
    
    setNudgeDismissalData(newDismissalData);
    localStorage.setItem('nudge-dismissal-data', JSON.stringify(newDismissalData));
  };

  const shouldShowNudge = () => {
    if (showQuestionnaire || questionnaireActive) return false;
    
    if (!user) {
      // Guest user logic - implement 3-strike rule with cooldown
      const guestData = nudgeDismissalData.guest;
      
      console.log('🎯 Guest nudge check:', { 
        count: guestData.count, 
        lastDismissed: guestData.lastDismissed,
        shouldShow: guestData.count < 3 || (guestData.count >= 3 && 
          (Date.now() - guestData.lastDismissed) / (1000 * 60 * 60) >= 24)
      });
      
      // If dismissed 3+ times, check cooldown (24 hours)
      if (guestData.count >= 3) {
        const hoursSinceLastDismissal = (Date.now() - guestData.lastDismissed) / (1000 * 60 * 60);
        return hoursSinceLastDismissal >= 24; // Show again after 24 hours
      }
      
      // Show nudge if less than 3 dismissals
      return true;
    }
    
    // Authenticated user logic
    const authData = nudgeDismissalData.authenticated;
    
    console.log('🔐 Auth nudge check:', { 
      dismissed: authData.dismissed,
      userType: nudgeStatus?.user_type,
      shouldShowFromStatus: nudgeStatus?.should_show_nudge
    });
    
    // Use the new questionnaire progress status
    if (businessProfileProgress) {
      // Never show for completed profiles
      if (businessProfileProgress.status === 'completed') {
        return false;
      }
      
      // Always show for in-progress or paused questionnaires (unless dismissed)
      if (businessProfileProgress.status === 'in_progress' || businessProfileProgress.status === 'paused') {
        return !authData.dismissed;
      }
      
      // Show for not_started if not dismissed
      if (businessProfileProgress.status === 'not_started') {
        return !authData.dismissed;
      }
      
      // Default: don't show
      return false;
    }
    
    // Fallback to old nudge status
    if (nudgeStatus?.user_type === 'completed') {
      return false;
    }
    
    if (!authData.dismissed) return nudgeStatus?.should_show_nudge || false;
    
    if (nudgeStatus?.user_type === 'in_progress') {
      return nudgeStatus.should_show_nudge;
    }
    
    return nudgeStatus?.should_show_nudge || false;
  };

  const getNudgeUserType = () => {
    if (!user) return 'guest';
    
    // Use the new questionnaire progress status
    if (businessProfileProgress) {
      return businessProfileProgress.status === 'completed' ? 'completed' :
             businessProfileProgress.status === 'in_progress' ? 'in_progress' :
             businessProfileProgress.status === 'paused' ? 'in_progress' :
             'not_started';
    }
    
    return nudgeStatus?.user_type || 'not_started';
  };


  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const currentInput = input.trim();
    
    // Check if we're in questionnaire mode
    if (questionnaireActive) {
      // Handle questionnaire commands
      if (currentInput.toLowerCase() === 'skip') {
        setInput('');
        await handleQuestionnaireCommand('skip');
        setTimeout(() => textareaRef.current?.focus(), 100);
        return;
      }
      if (currentInput.toLowerCase() === 'pause') {
        setInput('');
        await handleQuestionnaireCommand('pause');
        setTimeout(() => textareaRef.current?.focus(), 100);
        return;
      }
      if (currentInput.toLowerCase() === 'previous') {
        setInput('');
        await handleQuestionnaireCommand('previous');
        setTimeout(() => textareaRef.current?.focus(), 100);
        return;
      }
      
      // Submit answer to questionnaire
      setInput('');
      await submitQuestionnaireAnswer(currentInput);
      // Restore focus after submission
      setTimeout(() => {
        if (textareaRef.current) {
          textareaRef.current.focus();
        }
      }, 100);
      return;
    }
    
    // Check for questionnaire resume command
    if (currentInput.toLowerCase() === 'resume') {
      setInput('');
      await handleQuestionnaireCommand('resume');
      return;
    }

    // Create session if needed (will show auth if not logged in)
    const canProceed = await createNewSessionIfNeeded();
    if (!canProceed) return;

    const userMessage = { role: 'user', content: currentInput };
    setInput('');
    setMessages(prev => [...prev, userMessage]);
    setLoading(true);

    // Hide nudge when user starts regular chatting
    if (user) {
      // For authenticated users, mark nudge as dismissed
      const newDismissalData = {
        ...nudgeDismissalData,
        authenticated: { dismissed: true, lastDismissed: Date.now() }
      };
      setNudgeDismissalData(newDismissalData);
      localStorage.setItem('nudge-dismissal-data', JSON.stringify(newDismissalData));
    } else {
      // For guest users, increment dismissal count
      const newCount = nudgeDismissalData.guest.count + 1;
      const newDismissalData = {
        ...nudgeDismissalData,
        guest: { 
          count: newCount, 
          lastDismissed: Date.now() 
        }
      };
      setNudgeDismissalData(newDismissalData);
      localStorage.setItem('nudge-dismissal-data', JSON.stringify(newDismissalData));
    }

    try {
      // Prepare conversation history
      const conversationHistory = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      // Prepare chat context node (ONLY if explicitly set via the button)
      let chatContextNodeData = null;
      if (chatContextNode) {
        const properties = chatContextNode.properties || {};
        const fullData = properties.fullData || {};

        chatContextNodeData = {
          id: chatContextNode.id,
          name: properties.name || fullData.label || chatContextNode.caption,
          type: properties.category || fullData.type || 'Uncategorized',
          description: properties.description || fullData.content,
          theme: properties.theme || fullData.theme,
          labels: chatContextNode.labels || []
        };
      }

      // Use streaming endpoint
      const response = await fetch(`${API_URL}/api/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: currentInput,
          conversation_history: conversationHistory,
          chat_context_node: chatContextNodeData,
          user_id: user.id,
          session_id: currentSession.id,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let assistantResponse = { role: 'assistant', content: '', context: [] };

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          setMessages(prev => [...prev, assistantResponse]);
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.type === 'metadata') {
                assistantResponse.context = data.context;
              } else if (data.type === 'content') {
                assistantResponse.content += data.text;
              } else if (data.type === 'error') {
                throw new Error(data.message);
              }
            } catch (parseError) {
              console.error('Error parsing stream data:', parseError);
            }
          }
        }
      }
    } catch (error) {
      console.error('Error with streaming, attempting fallback:', error);
      
      try {
        // Fallback to regular chat endpoint
        const fallbackResponse = await axios.post(`${API_URL}/api/chat`, {
          question: currentInput,
          conversation_history: messages.map(msg => ({ role: msg.role, content: msg.content })),
          // Only include chat context node, not selected node
          chat_context_node: chatContextNode ? {
            id: chatContextNode.id,
            name: (chatContextNode.properties || chatContextNode).name || (chatContextNode.properties || chatContextNode).label,
            type: (chatContextNode.properties || chatContextNode).type || 'Uncategorized',
            description: (chatContextNode.properties || chatContextNode).description || (chatContextNode.properties || chatContextNode).content,
            theme: (chatContextNode.properties || chatContextNode).theme,
            labels: chatContextNode.labels || []
          } : null
        });

        const assistantMessage = {
          role: 'assistant',
          content: fallbackResponse.data.answer,
          context: fallbackResponse.data.context
        };
        setMessages(prev => [...prev, assistantMessage]);
        console.log(`Fallback successful.`);

      } catch (fallbackError) {
        console.error('Fallback also failed:', fallbackError);
        const errorMessage = {
          role: 'assistant',
          content: 'Sorry, I encountered an error while processing your request. Please try again.',
          isError: true
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Dynamic placeholder text based on context
  const placeholderText = questionnaireActive
    ? 'Write your answer here.'
    : chatContextNode
      ? `Ask questions about "${(chatContextNode.properties ? chatContextNode.properties.name : chatContextNode.name) || (chatContextNode.properties ? chatContextNode.properties.label : chatContextNode.label)}"...`
      : 'Ask about your biggest business challenges and get personalized answers';

  // Show selected node indicator (for currently selected node, not chat context)
  const selectedNodeInfo = selectedNode ? (
    <div className="selected-node-indicator">
      <span className="node-type">{selectedNode.properties?.type || 'Node'}</span>
      <span className="node-name">{(selectedNode.properties ? selectedNode.properties.name : selectedNode.name) || (selectedNode.properties ? selectedNode.properties.label : selectedNode.label)}</span>
    </div>
  ) : null;

  // Handle authentication success
  const handleAuthSuccess = (user) => {
    setUser(user);
    setShowAuth(false);
  };


  return (
    <>
      {/* Focus Mode Overlay */}
      
      <div className={`chat-panel ${isCollapsed ? 'collapsed' : ''} ${isFullscreen ? 'fullscreen' : ''} ${questionnaireActive ? 'questionnaire-active' : ''} ${messages.length === 0 ? 'no-messages' : ''} ${hasMessagesEver && messages.length > 0 ? 'has-messages' : ''}`}>
      {/* Authentication Modal */}
      {showAuth && (
        <Authentication 
          onAuthSuccess={handleAuthSuccess}
          onClose={() => setShowAuth(false)}
        />
      )}

      {/* Business Profile Questionnaire Modal */}
      {showQuestionnaire && user && (
        <div className="questionnaire-modal-overlay">
          <BusinessProfileQuestionnaire
            user={user}
            onComplete={handleQuestionnaireComplete}
            onProgress={handleQuestionnaireProgress}
            onClose={() => setShowQuestionnaire(false)}
            mode="modal"
          />
        </div>
      )}

      {/* Chat-integrated questionnaire progress indicator */}
      {questionnaireActive && !isCollapsed && (
        <div className="questionnaire-progress-indicator">
          <span>Business Profile Question {questionnaireProgress.current} of {questionnaireProgress.total}</span>
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${(questionnaireProgress.current / questionnaireProgress.total) * 100}%` }}
            />
          </div>
          <div className="questionnaire-commands">
            <span>Type "skip" or "previous" to navigate. Type "pause" to exit and finish later.</span>
          </div>
        </div>
      )}

      {messages.length > 0 && (
        <div className="chat-header" onClick={() => {
          setIsCollapsed(!isCollapsed);
          if (!isCollapsed && isFullscreen) {
            // Exit fullscreen when collapsing
            setIsFullscreen(false);
          }
        }}>
          <h3 className="chat-title">Chat</h3>
          {selectedNodeInfo}
          <div className="chat-controls">
            <button 
              className="chat-toggle fullscreen-toggle" 
              onClick={(e) => {
                e.stopPropagation();
                setIsFullscreen(!isFullscreen);
                if (isCollapsed) setIsCollapsed(false); // Expand if collapsed when going fullscreen
              }}
              aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
            >
              <span>{isFullscreen ? 'Exit Full Screen' : 'Full Screen'}</span>
              {isFullscreen ? (
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M8 3v3a2 2 0 0 1-2 2H3"></path>
                  <path d="M21 8h-3a2 2 0 0 1-2-2V3"></path>
                  <path d="M3 16h3a2 2 0 0 1 2 2v3"></path>
                  <path d="M16 21v-3a2 2 0 0 1 2-2h3"></path>
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M15 3h6v6"></path>
                  <path d="M9 21H3v-6"></path>
                  <path d="M21 3l-7 7"></path>
                  <path d="M3 21l7-7"></path>
                </svg>
              )}
            </button>
            <button className="chat-toggle" aria-label={isCollapsed ? 'Expand chat' : 'Collapse chat'}>
              <span>{isCollapsed ? 'Expand' : 'Collapse'}</span>
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                {isCollapsed ? <polyline points="18 15 12 9 6 15"></polyline> : <polyline points="6 9 12 15 18 9"></polyline>}
              </svg>
            </button>
          </div>
        </div>
      )}
      {(!isCollapsed || messages.length === 0) && (
        <>
          {messages.length > 0 && (
            <div className="messages" aria-live="polite">
              {messages.map((msg, idx) => (
                <div key={idx} className={`message-wrapper ${msg.role}`}>
                  <div className="message">
                    <div className="message-content">
                      {(msg.role === 'assistant') ? (
                        <div className="markdown-content">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                        </div>
                      ) : (
                        msg.content
                      )}
                    </div>
                  </div>
                </div>
              ))}
              {loading && (
                <div className="message-wrapper assistant" aria-live="polite" aria-busy="true">
                  <div className="message loading">
                    <div className="dot-flashing"></div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}

          {/* Business Profile Nudge Banner */}
          {shouldShowNudge() && (
            <ProfileNudgeBanner
              user={user}
              progress={businessProfileProgress}
              onStartQuestionnaire={handleStartQuestionnaire}
              onDismiss={handleNudgeDismiss}
              onOpenAuth={onOpenSidebarAuth || (() => setShowAuth(true))}
              userType={getNudgeUserType()}
              variant="default"
              isVisible={true}
              canDismiss={true}
              preferredMode="chat"
            />
          )}
          
          {/* Context Pills Container - NEW */}
          <div 
            className="context-pills-container" 
            aria-live="polite" 
            aria-atomic="false"
            role="region"
            aria-label="Chat context nodes"
          >
            {chatContextNode && (
              <div className="context-pill" role="group" aria-label={`Chat context: ${chatContextNode.properties?.name || chatContextNode.name || 'Unknown node'}`}>
                <span className="pill-text">
                  {chatContextNode.properties?.name || chatContextNode.name || chatContextNode.properties?.label || chatContextNode.label || 'Unknown'}
                </span>
                <button 
                  className="pill-remove-btn"
                  onClick={onClearChatContext}
                  aria-label={`Remove "${chatContextNode.properties?.name || chatContextNode.name || 'this node'}" from chat context`}
                  title="Remove from chat context"
                >
                  &times;
                </button>
              </div>
            )}
            
          </div>
          
          <div className="input-area">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholderText}
              disabled={loading}
              rows={1}
              aria-label="Chat message input"
            />
            <button 
              onClick={sendMessage} 
              disabled={loading || !input.trim()} 
              title="Send message" 
              aria-label="Send message"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M22 2L11 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          </div>

        </>
      )}
    </div>
    </>
  );
});

ChatPanel.displayName = 'ChatPanel';

export default ChatPanel;