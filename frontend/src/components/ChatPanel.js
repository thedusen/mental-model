import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './ChatPanel.css';

function ChatPanel({ selectedNode }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const textareaRef = useRef(null);

  useEffect(() => {
    if (textareaRef.current) {
      // Reset height to 'auto' to ensure it shrinks when text is deleted
      textareaRef.current.style.height = 'auto';
      // Set the height to the scroll height to expand with content
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = { type: 'user', content: input };
    setMessages([...messages, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await axios.post('/api/chat', { question: input });
      const assistantMessage = {
        type: 'assistant',
        content: response.data.answer,
        context: response.data.context
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, {
        type: 'error',
        content: 'Sorry, I encountered an error.'
      }]);
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

  return (
    <div className={`chat-panel ${isCollapsed ? 'collapsed' : ''} ${messages.length === 0 ? 'no-messages' : ''}`}>
      {messages.length > 0 && (
        <div className="chat-header" onClick={() => setIsCollapsed(!isCollapsed)}>
          <h3 className="chat-title">Chat</h3>
          <button className="chat-toggle" aria-label={isCollapsed ? 'Expand chat' : 'Collapse chat'}>
            <span>{isCollapsed ? 'Expand' : 'Collapse'}</span>
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              {isCollapsed ? <polyline points="18 15 12 9 6 15"></polyline> : <polyline points="6 9 12 15 18 9"></polyline>}
            </svg>
          </button>
        </div>
      )}
      {(!isCollapsed || messages.length === 0) && (
        <>
          {messages.length > 0 && (
            <div className="messages" aria-live="polite">
              {messages.map((msg, idx) => (
                <div key={idx} className={`message-wrapper ${msg.type}`}>
                  <div className="message">
                    {msg.type === 'assistant' ? (
                      <div className="markdown-content">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                      </div>
                    ) : (
                      msg.content
                    )}
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