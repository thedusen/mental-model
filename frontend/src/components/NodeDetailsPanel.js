import React from 'react';
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

function NodeDetailsPanel({ selectedNode, isCollapsed, onToggleCollapse }) {
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

            <div className="card-footer">
              💡 Ask questions about this in the chat.
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