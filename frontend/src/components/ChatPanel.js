import React, { useState } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './ChatPanel.css';

function ChatPanel({ selectedNode }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(true);

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
    : 'Ask about business mental models...';

  return (
    <div className={`chat-panel ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="chat-header" onClick={() => setIsCollapsed(!isCollapsed)}>
        <h3 className="chat-title">Chat with the Mental Model</h3>
        <button className="chat-toggle" aria-label={isCollapsed ? 'Expand chat' : 'Collapse chat'}>
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            {isCollapsed ? <polyline points="18 15 12 9 6 9"></polyline> : <polyline points="6 9 12 15 18 9"></polyline>}
          </svg>
        </button>
      </div>
      {!isCollapsed && (
        <>
          <div className="messages">
            {messages.length === 0 && (
              <div className="welcome-message">
                <div className="welcome-icon">💬</div>
                <h4>Start a conversation</h4>
                <p>Ask about concepts, patterns, and relationships in the mental model.</p>
              </div>
            )}
            
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
              <div className="message-wrapper assistant">
                <div className="message loading">
                  <div className="dot-flashing"></div>
                </div>
              </div>
            )}
          </div>
          
          <div className="input-area">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={placeholderText}
              disabled={loading}
              rows={1}
            />
            <button onClick={sendMessage} disabled={loading || !input.trim()} aria-label="Send message">
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