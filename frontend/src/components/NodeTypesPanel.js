import React, { useState } from 'react';
import './NodeTypesPanel.css';

const nodeTypesData = [
  { name: 'Theme', count: 70, color: '#F4B8A2' },
  { name: 'Value Framework', count: 168, color: '#A3D9D2' },
  { name: 'Cognitive Tensions', count: 132, color: '#A9C7E8' },
  { name: 'Decision Architecture', count: 105, color: '#C3B4E5' },
  { name: 'Adaptive Core', count: 88, color: '#F9D6B3' },
  { name: 'Energy Patterns', count: 36, color: '#E9C3E1' },
  { name: 'Uncategorized', count: 14, color: '#E0E0E0' },
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
        <button className="panel-toggle" aria-label={isCollapsed ? 'Expand legend' : 'Collapse legend'}>
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            {isCollapsed ? <polyline points="6 9 12 15 18 9"></polyline> : <polyline points="18 15 12 9 6 9"></polyline>}
          </svg>
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