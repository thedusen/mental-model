import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './ChatPanel.css';

function ChatPanel({ selectedNode, onFullscreenChange }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [hasMessagesEver, setHasMessagesEver] = useState(false);
  const textareaRef = useRef(null);

  // Use environment variable for API URL, fallback to localhost for development
  let API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
  
  // Ensure the API URL has a protocol
  if (API_URL && !API_URL.startsWith('http://') && !API_URL.startsWith('https://')) {
    API_URL = `https://${API_URL}`;
  }

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

  // Notify parent component when fullscreen state changes
  useEffect(() => {
    if (onFullscreenChange) {
      onFullscreenChange(isFullscreen);
    }
  }, [isFullscreen, onFullscreenChange]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = { role: 'user', content: input.trim() };
    const currentInput = input.trim();
    setInput('');
    setMessages(prev => [...prev, userMessage]);
    setLoading(true);

    try {
      // Prepare conversation history - send last 15 messages (excluding the current one we just added)
      const conversationHistory = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      // Prepare selected node context if available
      let selectedNodeContext = null;
      if (selectedNode) {
        const properties = selectedNode.properties || selectedNode;
        selectedNodeContext = {
          id: selectedNode.id,
          name: properties.name || properties.label,
          type: properties.type || 'Uncategorized',
          description: properties.description || properties.content,
          theme: properties.theme,
          labels: selectedNode.labels || []
        };
      }

      // Create placeholder for streaming response
      const assistantMessage = {
        role: 'assistant',
        content: '',
        context: [],
        isStreaming: true
      };
      
      setMessages(prev => [...prev, assistantMessage]);

      // Use streaming endpoint for real-time responses
      const response = await fetch(`${API_URL}/api/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: currentInput,
          conversation_history: conversationHistory,
          selected_node: selectedNodeContext
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let streamingContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.type === 'metadata') {
                // Update context when received
                setMessages(prev => prev.map((msg, index) => 
                  index === prev.length - 1 
                    ? { ...msg, context: data.context }
                    : msg
                ));
              } else if (data.type === 'content') {
                // Append streaming text
                streamingContent += data.text;
                setMessages(prev => prev.map((msg, index) => 
                  index === prev.length - 1 
                    ? { ...msg, content: streamingContent }
                    : msg
                ));
              } else if (data.type === 'done') {
                // Mark streaming as complete
                setMessages(prev => prev.map((msg, index) => 
                  index === prev.length - 1 
                    ? { ...msg, content: data.full_response, isStreaming: false }
                    : msg
                ));
                console.log(`Sent ${conversationHistory.length} previous messages. Streaming complete.`);
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
      console.error('Error with streaming, falling back to regular chat:', error);
      
      try {
        // Fallback to regular chat endpoint
        const response = await axios.post(`${API_URL}/api/chat`, {
          question: currentInput,
          conversation_history: conversationHistory,
          selected_node: selectedNodeContext
        });

        const assistantMessage = {
          role: 'assistant',
          content: response.data.answer,
          context: response.data.context
        };

        setMessages(prev => {
          const newMessages = [...prev];
          // Replace the streaming placeholder with regular response
          newMessages[newMessages.length - 1] = assistantMessage;
          return newMessages;
        });
        
        console.log(`Fallback successful. Sent ${conversationHistory.length} previous messages.`);
      } catch (fallbackError) {
        console.error('Fallback also failed:', fallbackError);
        
        const errorMessage = {
          role: 'assistant',
          content: 'Sorry, I encountered an error while processing your request. Please try again.',
          isError: true
        };
        
        setMessages(prev => {
          const newMessages = [...prev];
          // Replace the last message (streaming placeholder) with error
          newMessages[newMessages.length - 1] = errorMessage;
          return newMessages;
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const placeholderText = selectedNode
    ? `Ask questions about "${(selectedNode.properties ? selectedNode.properties.name : selectedNode.name) || (selectedNode.properties ? selectedNode.properties.label : selectedNode.label)}"...`
    : 'Ask about concepts, patterns, and relationships in the mental model...';

  // Show selected node indicator
  const selectedNodeInfo = selectedNode ? (
    <div className="selected-node-indicator">
      <span className="node-type">{selectedNode.properties?.type || 'Node'}</span>
      <span className="node-name">{(selectedNode.properties ? selectedNode.properties.name : selectedNode.name) || (selectedNode.properties ? selectedNode.properties.label : selectedNode.label)}</span>
    </div>
  ) : null;

  return (
    <div className={`chat-panel ${isCollapsed ? 'collapsed' : ''} ${isFullscreen ? 'fullscreen' : ''} ${messages.length === 0 ? 'no-messages' : ''} ${hasMessagesEver && messages.length > 0 ? 'has-messages' : ''}`}>
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
                  <div className={`message ${msg.isStreaming ? 'streaming' : ''}`}>
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
            </div>
          )}
          
          <div className="input-area">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={placeholderText}
              disabled={loading}
              rows={1}
            />
            <button onClick={sendMessage} disabled={loading || !input.trim()} title="Send message" aria-label="Send message">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M22 2L11 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export default ChatPanel;