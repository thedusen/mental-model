import React, { useState } from 'react';
import './NodeTypesPanel.css';

const nodeTypesData = [
  { name: 'Theme', count: 70, color: '#DC2626' },
  { name: 'Value Framework', count: 168, color: '#059669' },
  { name: 'Cognitive Tensions', count: 132, color: '#2563EB' },
  { name: 'Decision Architecture', count: 105, color: '#7C3AED' },
  { name: 'Adaptive Core', count: 88, color: '#EA580C' },
  { name: 'Energy Patterns', count: 36, color: '#DB2777' },
  { name: 'Uncategorized', count: 14, color: '#64748B' },
];

function NodeTypesPanel({ onFilterChange }) {
  const [activeFilters, setActiveFilters] = useState([]);
  const [isCollapsed, setIsCollapsed] = useState(false);

  const handleTypeClick = (typeName) => {
    const newFilters = activeFilters.includes(typeName)
      ? activeFilters.filter((t) => t !== typeName)
      : [...activeFilters, typeName];
    
    setActiveFilters(newFilters);

    if (onFilterChange) {
      onFilterChange(newFilters);
    }
  };

  return (
    <div className={`node-types-panel ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="panel-header" onClick={() => setIsCollapsed(!isCollapsed)}>
        <h3 className="panel-title">Node Types</h3>
        <button className="panel-toggle">
          {isCollapsed ? '+' : '−'}
        </button>
      </div>
      {!isCollapsed && (
        <div className="panel-content">
          <ul className="types-list">
            {nodeTypesData.map((type) => (
              <li
                key={type.name}
                className={`type-item ${activeFilters.includes(type.name) ? 'active' : ''}`}
                onClick={() => handleTypeClick(type.name)}
              >
                <div className="type-info">
                  <span className="type-color-dot" style={{ backgroundColor: type.color }}></span>
                  <span className="type-name">{type.name}</span>
                </div>
                <span className="type-count">{type.count}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default NodeTypesPanel; 