import React, { useEffect, useRef } from 'react';
import './NodeDetailsPanel.css';

const getCategoryStyle = (category) => {
  const styles = {
    'Theme': { '--category-color': '#DC2626', '--category-bg': '#FEF2F2' },
    'VALUE FRAMEWORK': { '--category-color': '#059669', '--category-bg': '#F0FDF4' },
    'COGNITIVE TENSIONS': { '--category-color': '#2563EB', '--category-bg': '#EFF6FF' },
    'DECISION ARCHITECTURE': { '--category-color': '#7C3AED', '--category-bg': '#F5F3FF' },
    'ADAPTIVE CORE': { '--category-color': '#EA580C', '--category-bg': '#FFF7ED' },
    'ENERGY PATTERNS': { '--category-color': '#DB2777', '--category-bg': '#FDF2F8' },
    'Uncategorized': { '--category-color': '#64748B', '--category-bg': '#F8FAFC' }
  };
  return styles[category] || styles['Uncategorized'];
};

const DetailRow = ({ label, value, isContent = false }) => {
  if (!value) return null;
  return (
    <div className={`detail-row ${isContent ? 'content-row' : ''}`}>
      <span className="detail-label">{label}</span>
      <span className="detail-value">{value}</span>
    </div>
  );
};

function NodeDetailsPanel({ selectedNode, chatContextNode, onSetChatContext, isCollapsed, onToggleCollapse }) {
  const chatButtonRef = useRef(null);

  // Focus management: when a new node is selected, focus the chat button
  useEffect(() => {
    if (selectedNode && !isCollapsed && chatButtonRef.current) {
      // Small delay to ensure the panel is fully rendered
      setTimeout(() => {
        if (chatButtonRef.current) {
          chatButtonRef.current.focus();
        }
      }, 100);
    }
  }, [selectedNode, isCollapsed]);

  // Main render logic
  if (isCollapsed) {
    return (
      <div className="node-details-panel collapsed">
        <button onClick={onToggleCollapse} className="panel-toggle" aria-label="Expand sidebar">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
        </button>
      </div>
    );
  }

  const properties = selectedNode ? selectedNode.properties || selectedNode : null;
  const labels = selectedNode ? selectedNode.labels || [] : [];
  
  // Check if this node is currently in chat context
  const isInChatContext = chatContextNode && selectedNode && 
    (chatContextNode.id === selectedNode.id);

  // Handle chat context button click
  const handleChatContextClick = () => {
    if (isInChatContext) {
      // If already in context, we could remove it, but the UI expert suggested
      // either disabling the button or making it a "Remove from chat" button
      // For simplicity, we'll just disable when in context
      return;
    } else {
      onSetChatContext(selectedNode);
    }
  };

  return (
    <div className={`node-details-panel ${!selectedNode ? 'empty-state' : ''}`}>
      {selectedNode && (
        <div className="panel-header">
          <button onClick={onToggleCollapse} className="panel-toggle" aria-label="Collapse sidebar">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
          </button>
        </div>
      )}

      {!selectedNode && (
        <div className="empty-panel-header">
          <button onClick={onToggleCollapse} className="panel-toggle-with-text" aria-label="Collapse sidebar">
            <span>Collapse</span>
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
          </button>
        </div>
      )}

      <div className="panel-content" aria-live="polite">
        {/* Screen reader announcement for selected node */}
        {selectedNode && (
          <div className="sr-only" aria-live="polite">
            Showing details for {properties.name || properties.label}
          </div>
        )}
        
        {selectedNode ? (
          <div className="details-card" style={getCategoryStyle(properties.type)}>
            <div className="card-header">
              <div className="category-badge">
                {properties.type || 'Uncategorized'}
              </div>
              <h3 className="node-title">{properties.name || properties.label}</h3>
            </div>
            
            <div className="card-body">
              <DetailRow 
                label="Description" 
                value={properties.description || properties.content}
                isContent={true}
              />
              <DetailRow label="Node ID" value={selectedNode.id} />
              <DetailRow label="Theme" value={properties.theme} />
              <DetailRow label="Labels" value={labels.join(', ')} />
              <DetailRow label="Source Chunk" value={properties.source_chunk} />
            </div>

            {/* Chat Context Button */}
            <div className="card-actions">
              <button
                ref={chatButtonRef}
                data-chat-context-button
                onClick={handleChatContextClick}
                disabled={isInChatContext}
                className={`chat-context-button ${isInChatContext ? 'in-context' : ''}`}
                aria-label={
                  isInChatContext 
                    ? `Node "${properties.name || properties.label}" is already added to chat context`
                    : `Add "${properties.name || properties.label}" to chat context`
                }
                title={
                  isInChatContext 
                    ? 'This node is already in your chat context'
                    : 'Add this node to your chat context for more focused conversations'
                }
              >
                {isInChatContext ? (
                  <>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="check-icon">
                      <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                    Added to Chat
                  </>
                ) : (
                  <>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="chat-icon">
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                    </svg>
                    Chat with this node
                  </>
                )}
              </button>
            </div>

            <div className="card-footer">
              💡 {isInChatContext ? 'This node is now part of your conversation context.' : 'Click the button above to add this node to your chat context.'}
            </div>
          </div>
        ) : (
          <div className="empty-state-content">
            <div className="empty-icon">🎯</div>
            <p className="empty-title">Click a Node</p>
            <p className="empty-subtitle">Select any node on the graph to view its details here.</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default NodeDetailsPanel; 