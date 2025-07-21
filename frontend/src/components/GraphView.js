import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import { InteractiveNvlWrapper as NVL } from '@neo4j-nvl/react';
import axios from 'axios';

// Helper function to programmatically brighten a hex color
// This simulates the d3.brighter() function to restore the gradient effect
const brightenHexColor = (hex, percent) => {
  hex = hex.replace(/^\s*#|\s*$/g, '');
  if (hex.length === 3) {
    hex = hex.replace(/(.)/g, '$1$1');
  }
  const r = parseInt(hex.substr(0, 2), 16);
  const g = parseInt(hex.substr(2, 2), 16);
  const b = parseInt(hex.substr(4, 2), 16);

  const calculatedPercent = (100 + percent) / 100;

  const newR = Math.min(255, Math.floor(r * calculatedPercent));
  const newG = Math.min(255, Math.floor(g * calculatedPercent));
  const newB = Math.min(255, Math.floor(b * calculatedPercent));

  return `#${newR.toString(16).padStart(2, '0')}${newG.toString(16).padStart(2, '0')}${newB.toString(16).padStart(2, '0')}`;
};

function GraphView({ onNodeSelect, onCanvasClick, chatContextNode, filters }) {
  console.log('GraphView component rendering...');
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  // State to manage the legend's collapsed state
  const [isLegendMinimized, setIsLegendMinimized] = useState(false); 
  const [error, setError] = useState(null);
  const nvlRef = useRef(null);
  
  // Use environment variable for API URL, fallback to localhost for development
  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  useEffect(() => {
    console.log('GraphViewD3 useEffect running...');
    loadGraph();
  }, []);

  const loadGraph = async () => {
    console.log('Loading graph data...');
    try {
      const response = await axios.get(`${API_URL}/api/graph`);
      console.log('API response:', response.data);
      const { nodes, edges } = response.data;
      console.log('Processing nodes:', nodes?.length, 'edges:', edges?.length);
      setGraphData({ nodes, edges });
    } catch (error) {
      console.error('Error loading graph:', error);
      setError(error.message);
    }
  };

  const memoizedNodes = useMemo(() => {
    if (!graphData.nodes || graphData.nodes.length === 0) {
      return [];
    }
    
    // Restore the original D3 pastel color palette
    const typeColors = {
      'Theme': '#F4B8A2',
      'VALUE FRAMEWORK': '#A3D9D2',
      'COGNITIVE TENSIONS': '#A9C7E8',
      'DECISION ARCHITECTURE': '#C3B4E5',
      'ADAPTIVE CORE': '#F9D6B3',
      'ENERGY PATTERNS': '#E9C3E1',
      'Uncategorized': '#E0E0E0'
    };
    
    return graphData.nodes.map(node => {
      const isTheme = node.type === 'Theme';
      const isChatContext = chatContextNode && node.id === chatContextNode.id;
      const baseColor = typeColors[node.type] || typeColors['Uncategorized'];

      // Simulate the gradient: bright fill, original color border
      const fillColor = brightenHexColor(baseColor, 20); // 20% brighter for the center

      let finalNode = {
        id: node.id,
        caption: node.label,
        size: isTheme ? 40 : 25, // Slightly larger nodes
        color: fillColor,
        fontSize: isTheme ? 14 : 11,
        font: {
          color: '#1E293B', // Darker font for better readability on light backgrounds
          strokeWidth: 0,
          size: isTheme ? 14 : 11
        },
        type: 'circle',
        borderColor: baseColor, // Original pastel color as border
        borderWidth: isTheme ? 4 : 3, // Thicker border to enhance the two-tone effect
        shadowEnabled: true,
        shadowColor: 'rgba(0, 0, 0, 0.15)',
        shadowBlur: 8,
        shadowOffsetX: 3,
        shadowOffsetY: 3,
        properties: {
          name: node.label,
          description: node.description,
          category: node.type,
          fullData: node
        }
      };

      if (isChatContext) {
        finalNode = {
          ...finalNode,
          borderColor: '#10B981',
          borderWidth: 4,
          shadowEnabled: true,
          shadowColor: 'rgba(16, 185, 129, 0.4)',
          shadowBlur: 12,
          shadowOffsetX: 0,
          shadowOffsetY: 0,
        };
      }
      
      return finalNode;
    });
  }, [graphData.nodes, chatContextNode]);

  const memoizedRels = useMemo(() => {
    if (!graphData.edges || graphData.edges.length === 0) {
      return [];
    }
    return graphData.edges.map((edge, idx) => ({
      id: `rel-${idx}`,
      from: edge.from,
      to: edge.to,
      caption: edge.label,
      color: '#94A3B8',
      width: 2,
      length: 150,
      arrows: 'to',
      arrowStrikethrough: false,
      font: {
        size: 10,
        color: '#64748B',
        strokeWidth: 0,
        align: 'middle'
      },
      smooth: {
        enabled: true,
        type: 'continuous',
        roundness: 0.2
      }
    }));
  }, [graphData.edges]);

  // **THE FIX**: Wrap all callback props in `useCallback` to ensure their
  // references are stable across re-renders. This prevents the child component
  // from crashing due to unstable function references.
  const handleNodeClick = useCallback((node) => {
    console.log('Node clicked:', node);
    if (onNodeSelect) {
      onNodeSelect(node);
      
      setTimeout(() => {
        const detailsPanel = document.querySelector('.node-details-panel');
        if (detailsPanel && !detailsPanel.classList.contains('collapsed')) {
          const chatButton = detailsPanel.querySelector('[data-chat-context-button]');
          if (chatButton) {
            chatButton.focus();
          }
        }
      }, 100);
    }
  }, [onNodeSelect]);

  const handleCanvasClick = useCallback(() => {
    console.log('Canvas clicked - deselecting node');
    if (onCanvasClick) {
      onCanvasClick();
    }
  }, [onCanvasClick]);

  const handleLayoutDone = useCallback((nodes, rels) => {
    console.log('Layout computed');
  }, []);

  const mouseEventCallbacks = useMemo(() => ({
    onNodeClick: handleNodeClick,
    onCanvasClick: handleCanvasClick,
    onPan: (evt) => {
      // Pan interaction is handled automatically by the NVL library
      // This callback is just for tracking if needed
      console.log('Graph panned');
    },
    onZoom: (zoomLevel) => {
      // Zoom interaction is handled automatically by the NVL library
      // This callback is just for tracking if needed
      console.log('Graph zoomed to level:', zoomLevel);
    },
  }), [handleNodeClick, handleCanvasClick]);

  const nvlCallbacks = useMemo(() => ({
    onLayoutDone: handleLayoutDone,
  }), [handleLayoutDone]);

  const handleZoomIn = () => {
    if (nvlRef.current) {
      nvlRef.current.zoomIn();
    }
  };

  const handleZoomOut = () => {
    if (nvlRef.current) {
      nvlRef.current.zoomOut();
    }
  };

  const handleKeyDown = (event) => {
    // Only handle keyboard shortcuts if the focus is on the container itself, not child elements
    if (event.target === event.currentTarget) {
      if (event.key === '+' || event.key === '=') {
        event.preventDefault();
        handleZoomIn();
      } else if (event.key === '-') {
        event.preventDefault();
        handleZoomOut();
      }
    }
  };

  // **THE FIX**: This hardcoded list is now removed.
  // The legend will be generated dynamically by the NVL component.

  if (error) {
    return (
      <div style={{ padding: '20px', color: 'red', backgroundColor: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '8px', margin: '20px' }}>
        <h3>Graph Loading Error</h3>
        <p>Failed to load graph data: {error}</p>
        <button onClick={loadGraph} style={{ marginTop: '10px', padding: '8px 16px' }}>
          Retry
        </button>
      </div>
    );
  }

  console.log('Rendering GraphView with data:', memoizedNodes.length, 'nodes');

  return (
    <div 
      style={{ position: 'relative', width: '100%', height: '100%' }}
      onKeyDown={handleKeyDown}
      tabIndex="0"
      role="application"
      aria-label="Knowledge graph visualization..."
    >
      {/* Enhanced Zoom Controls */}
      <div style={{
        position: 'absolute',
        top: '16px',
        right: '16px',
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        gap: '8px'
      }}>
        <button
          onClick={handleZoomIn}
          style={{
            width: '44px',
            height: '44px',
            backgroundColor: '#FFFFFF',
            border: '1px solid #E2E8F0',
            borderRadius: '12px',
            cursor: 'pointer',
            fontSize: '18px',
            fontWeight: '500',
            color: '#475569',
            boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
            transition: 'all 0.2s ease',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          title="Zoom In (or press +)"
          aria-label="Zoom in to the graph"
          onMouseEnter={(e) => {
            e.target.style.backgroundColor = '#F8FAFC';
            e.target.style.borderColor = '#CBD5E1';
            e.target.style.transform = 'translateY(-1px)';
            e.target.style.boxShadow = '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)';
          }}
          onMouseLeave={(e) => {
            e.target.style.backgroundColor = '#FFFFFF';
            e.target.style.borderColor = '#E2E8F0';
            e.target.style.transform = 'translateY(0)';
            e.target.style.boxShadow = '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)';
          }}
        >
          ＋
        </button>
        <button
          onClick={handleZoomOut}
          style={{
            width: '44px',
            height: '44px',
            backgroundColor: '#FFFFFF',
            border: '1px solid #E2E8F0',
            borderRadius: '12px',
            cursor: 'pointer',
            fontSize: '18px',
            fontWeight: '500',
            color: '#475569',
            boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
            transition: 'all 0.2s ease',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          title="Zoom Out (or press -)"
          aria-label="Zoom out from the graph"
          onMouseEnter={(e) => {
            e.target.style.backgroundColor = '#F8FAFC';
            e.target.style.borderColor = '#CBD5E1';
            e.target.style.transform = 'translateY(-1px)';
            e.target.style.boxShadow = '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)';
          }}
          onMouseLeave={(e) => {
            e.target.style.backgroundColor = '#FFFFFF';
            e.target.style.borderColor = '#E2E8F0';
            e.target.style.transform = 'translateY(0)';
            e.target.style.boxShadow = '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)';
          }}
        >
          －
        </button>
      </div>

      {/* **THE FIX**: The custom legend component is completely removed from here. */}

      {memoizedNodes.length > 0 && (
        <NVL
          ref={nvlRef}
          nodes={memoizedNodes}
          rels={memoizedRels}
          nvlOptions={{
            layout: 'force-directed',
            initialZoom: 1,
            allowDynamicMinZoom: true,
            minZoom: 0.1,
            maxZoom: 8,
            // New options to control the NVL legend
            legend: {
              enabled: true,
              orientation: 'top-left', // Move legend to top-left
              isCollapsed: isLegendMinimized, // Control collapse state
              onToggle: () => setIsLegendMinimized(!isLegendMinimized), // Handle toggle
            },
          }}
          mouseEventCallbacks={mouseEventCallbacks}
          nvlCallbacks={nvlCallbacks}
        />
      )}
    </div>
  );
}

export default GraphView; 