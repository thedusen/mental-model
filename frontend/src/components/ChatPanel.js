import React, { useState } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './ChatPanel.css';

function ChatPanel({ selectedNode }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isNodeDetailsExpanded, setIsNodeDetailsExpanded] = useState(true);

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

  // Get category icon and color
  const getCategoryInfo = (category) => {
    const categoryMap = {
      'Theme': { color: '#DC2626', bg: '#FEF2F2' },
      'VALUE FRAMEWORK': { color: '#059669', bg: '#F0FDF4' },
      'COGNITIVE TENSIONS': { color: '#2563EB', bg: '#EFF6FF' },
      'DECISION ARCHITECTURE': { color: '#7C3AED', bg: '#F5F3FF' },
      'ADAPTIVE CORE': { color: '#EA580C', bg: '#FFF7ED' },
      'ENERGY PATTERNS': { color: '#DB2777', bg: '#FDF2F8' },
      'Uncategorized': { color: '#64748B', bg: '#F8FAFC' }
    };
    return categoryMap[category] || categoryMap['Uncategorized'];
  };

  return (
    <div className="chat-panel">
      <div className="selected-node">
        {selectedNode ? (
          <div style={{
            border: '1px solid #E2E8F0',
            borderRadius: '12px',
            backgroundColor: '#FFFFFF',
            boxShadow: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
            overflow: 'hidden'
          }}>
            {/* Accordion Header - Always Visible */}
            <div 
              onClick={() => setIsNodeDetailsExpanded(!isNodeDetailsExpanded)}
              style={{
                padding: '16px 20px',
                cursor: 'pointer',
                borderBottom: isNodeDetailsExpanded ? '1px solid #E2E8F0' : 'none',
                transition: 'all 0.15s ease',
                backgroundColor: isNodeDetailsExpanded ? '#FAFAFA' : '#FFFFFF'
              }}
            >
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'space-between',
                gap: '12px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
                  {/* Category badge */}
                  <div style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    backgroundColor: getCategoryInfo(selectedNode.properties.category).bg,
                    color: getCategoryInfo(selectedNode.properties.category).color,
                    padding: '4px 8px',
                    borderRadius: '6px',
                    fontSize: '12px',
                    fontWeight: '500',
                    border: `1px solid ${getCategoryInfo(selectedNode.properties.category).color}20`
                  }}>
                    {selectedNode.properties.category || 'Uncategorized'}
                  </div>

                  {/* Node title */}
                  <h3 style={{
                    fontSize: '16px',
                    fontWeight: '600',
                    color: '#0F172A',
                    margin: 0,
                    lineHeight: '1.4',
                    flex: 1
                  }}>
                    {selectedNode.properties.name}
                  </h3>
                </div>

                {/* Expand/Collapse Icon */}
                <div style={{
                  fontSize: '14px',
                  color: '#64748B',
                  transition: 'transform 0.15s ease',
                  transform: isNodeDetailsExpanded ? 'rotate(180deg)' : 'rotate(0deg)'
                }}>
                  ▼
                </div>
              </div>
            </div>

            {/* Accordion Content - Expandable */}
            {isNodeDetailsExpanded && (
              <div style={{
                padding: '20px',
                animation: 'fadeIn 0.15s ease'
              }}>
                {/* Node description */}
                {selectedNode.properties.description && (
                  <div style={{
                    backgroundColor: '#F8FAFC',
                    border: '1px solid #E2E8F0',
                    borderRadius: '8px',
                    padding: '16px',
                    marginBottom: '16px'
                  }}>
                    <div style={{
                      fontSize: '13px',
                      fontWeight: '500',
                      color: '#475569',
                      marginBottom: '8px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}>
                      📝 Description
                    </div>
                    <p style={{
                      fontSize: '14px',
                      color: '#1E293B',
                      lineHeight: '1.5',
                      margin: 0
                    }}>
                      {selectedNode.properties.description}
                    </p>
                  </div>
                )}

                {/* Additional node metadata */}
                {selectedNode.properties.fullData && (
                  <div style={{ 
                    display: 'grid',
                    gap: '12px'
                  }}>
                    {/* Node ID */}
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '8px 12px',
                      backgroundColor: '#F1F5F9',
                      borderRadius: '6px',
                      fontSize: '12px'
                    }}>
                      <span style={{ 
                        fontWeight: '500', 
                        color: '#475569',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px'
                      }}>
                        🔑 Node ID
                      </span>
                      <span style={{ 
                        color: '#64748B',
                        fontFamily: 'monospace',
                        fontSize: '11px'
                      }}>
                        {selectedNode.id}
                      </span>
                    </div>

                    {/* Node labels */}
                    {selectedNode.labels && selectedNode.labels.length > 0 && (
                      <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        padding: '8px 12px',
                        backgroundColor: '#F1F5F9',
                        borderRadius: '6px',
                        fontSize: '12px'
                      }}>
                        <span style={{ 
                          fontWeight: '500', 
                          color: '#475569',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}>
                          🏷️ Labels
                        </span>
                        <span style={{ color: '#64748B' }}>
                          {selectedNode.labels.join(', ')}
                        </span>
                      </div>
                    )}
                  </div>
                )}

                {/* Action hint */}
                <div style={{
                  marginTop: '16px',
                  padding: '12px',
                  backgroundColor: '#F0F9FF',
                  border: '1px solid #0EA5E9',
                  borderRadius: '8px',
                  fontSize: '13px',
                  color: '#0C4A6E',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  💡 <span>Ask questions about this concept in the chat below</span>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div style={{
            border: '2px dashed #CBD5E1',
            borderRadius: '12px',
            padding: '40px 20px',
            textAlign: 'center',
            backgroundColor: '#F8FAFC',
            color: '#64748B'
          }}>
            <div style={{ fontSize: '32px', marginBottom: '12px' }}>🎯</div>
            <p style={{ 
              margin: 0, 
              fontSize: '14px',
              fontWeight: '500'
            }}>
              Click a node to explore details
            </p>
            <p style={{ 
              margin: '8px 0 0 0', 
              fontSize: '12px',
              color: '#94A3B8'
            }}>
              Select any node in the graph to see its information and ask questions about it
            </p>
          </div>
        )}
      </div>
      
      <div className="messages">
        {messages.map((msg, idx) => {
          const content = typeof msg.content === 'string' ? msg.content : String(msg.content || '');
          
          return (
            <div key={idx} className={`message ${msg.type}`}>
              {msg.type === 'assistant' ? (
                <div className="markdown-content">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {content}
                  </ReactMarkdown>
                </div>
              ) : (
                content
              )}
            </div>
          );
        })}
        {loading && <div className="message loading">Thinking...</div>}
      </div>
      
      <div className="input-area">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Ask about business mental models..."
          disabled={loading}
        />
        <button onClick={sendMessage} disabled={loading}>
          Send
        </button>
      </div>
    </div>
  );
}

export default ChatPanel;