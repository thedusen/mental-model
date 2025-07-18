import React, { useEffect, useRef, useState } from 'react';
import { InteractiveNvlWrapper as NVL } from '@neo4j-nvl/react';
import axios from 'axios';

function GraphView({ onNodeSelect }) {
  const [graphData, setGraphData] = useState({ nodes: [], relationships: [] });
  const nvlRef = useRef(null);

  useEffect(() => {
    loadGraph();
  }, []);

  const loadGraph = async () => {
    try {
      const response = await axios.get('/api/graph');
      const { nodes, edges } = response.data;

      // Transform data for NVL with enhanced styling for different node types
      const nvlNodes = nodes.map(node => {
        const isTheme = node.type === 'Theme';
        
        // Shadcn-inspired color palette - more muted and professional
        const typeColors = {
          'Theme': '#DC2626',                    // Red-600 for themes
          'VALUE FRAMEWORK': '#059669',          // Emerald-600 for value frameworks
          'COGNITIVE TENSIONS': '#2563EB',       // Blue-600 for cognitive tensions  
          'DECISION ARCHITECTURE': '#7C3AED',    // Violet-600 for decision architecture
          'ADAPTIVE CORE': '#EA580C',           // Orange-600 for adaptive core
          'ENERGY PATTERNS': '#DB2777',         // Pink-600 for energy patterns
          'Uncategorized': '#64748B'            // Slate-500 for uncategorized
        };

        return {
          id: node.id,
          labels: [node.type || 'Entity'],
          properties: {
            name: node.label,
            description: node.description,
            category: node.type,
            fullData: node  // Store the full node data for the chat panel
          },
          caption: node.label,
          color: typeColors[node.type] || typeColors['Uncategorized'],
          size: isTheme ? 55 : 40  // Make themes larger
        };
      });

      const nvlRelationships = edges.map((edge, idx) => ({
        id: `rel-${idx}`,
        from: edge.from,
        to: edge.to,
        caption: edge.label,
        color: edge.label === 'BELONGS_TO' ? '#DC2626' : '#64748B'  // Red for theme connections
      }));

      setGraphData({
        nodes: nvlNodes,
        relationships: nvlRelationships
      });
    } catch (error) {
      console.error('Error loading graph:', error);
    }
  };

  // Zoom control functions
  const zoomIn = () => {
    if (nvlRef.current) {
      const currentZoom = nvlRef.current.getScale();
      nvlRef.current.setZoom(currentZoom * 1.2);
    }
  };

  const zoomOut = () => {
    if (nvlRef.current) {
      const currentZoom = nvlRef.current.getScale();
      nvlRef.current.setZoom(currentZoom * 0.8);
    }
  };

  const fitGraph = () => {
    if (nvlRef.current) {
      nvlRef.current.fit();
    }
  };

  const resetZoom = () => {
    if (nvlRef.current) {
      nvlRef.current.resetZoom();
    }
  };

  // Mouse event callbacks for InteractiveNvlWrapper
  const mouseEventCallbacks = {
    onNodeClick: (node, hitTargets, event) => {
      console.log('Node clicked:', node);
      if (onNodeSelect) {
        onNodeSelect(node);
      }
    },
    onNodeDoubleClick: (node, hitTargets, event) => {
      console.log('Node double-clicked:', node);
      // Zoom to the clicked node and its neighbors
      if (nvlRef.current) {
        nvlRef.current.zoomToNodes([node.id]);
      }
    },
    onCanvasClick: (event) => {
      console.log('Canvas clicked');
      // Deselect nodes when clicking on empty space
      if (onNodeSelect) {
        onNodeSelect(null);
      }
    },
    onZoom: (zoomLevel) => {
      console.log('Zoom level:', zoomLevel);
    },
    onPan: (event) => {
      console.log('Panning');
    }
  };

  // NVL callbacks
  const nvlCallbacks = {
    onLayoutDone: () => {
      console.log('Layout done, fitting graph to view');
      // Auto-fit the graph to show all nodes when layout completes
      if (nvlRef.current) {
        nvlRef.current.fit();
      }
    }
  };

  return (
    <div style={{ 
      width: '100%', 
      height: '100%', 
      minHeight: '400px', 
      position: 'relative',
      backgroundColor: '#F1F5F9' // Slightly darker grey for button contrast
    }}>
      {/* Shadcn-inspired Zoom Controls */}
      <div style={{
        position: 'absolute',
        top: '16px',
        right: '16px',
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        gap: '4px'
      }}>
        <button 
          onClick={zoomIn}
          style={{
            width: '40px',
            height: '40px',
            border: '1px solid #E2E8F0',
            borderRadius: '8px',
            backgroundColor: '#FFFFFF',
            color: '#1E293B',
            cursor: 'pointer',
            fontSize: '16px',
            fontWeight: '500',
            transition: 'all 0.15s ease',
            boxShadow: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          title="Zoom In"
          onMouseEnter={(e) => {
            e.target.style.backgroundColor = '#F8FAFC';
            e.target.style.borderColor = '#CBD5E1';
            e.target.style.boxShadow = '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)';
          }}
          onMouseLeave={(e) => {
            e.target.style.backgroundColor = '#FFFFFF';
            e.target.style.borderColor = '#E2E8F0';
            e.target.style.boxShadow = '0 1px 2px 0 rgb(0 0 0 / 0.05)';
          }}
        >
          ＋
        </button>
        
        <button 
          onClick={zoomOut}
          style={{
            width: '40px',
            height: '40px',
            border: '1px solid #E2E8F0',
            borderRadius: '8px',
            backgroundColor: '#FFFFFF',
            color: '#1E293B',
            cursor: 'pointer',
            fontSize: '16px',
            fontWeight: '500',
            transition: 'all 0.15s ease',
            boxShadow: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          title="Zoom Out"
          onMouseEnter={(e) => {
            e.target.style.backgroundColor = '#F8FAFC';
            e.target.style.borderColor = '#CBD5E1';
            e.target.style.boxShadow = '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)';
          }}
          onMouseLeave={(e) => {
            e.target.style.backgroundColor = '#FFFFFF';
            e.target.style.borderColor = '#E2E8F0';
            e.target.style.boxShadow = '0 1px 2px 0 rgb(0 0 0 / 0.05)';
          }}
        >
          －
        </button>
      </div>

      {/* Shadcn-inspired Legend */}
      <div style={{
        position: 'absolute',
        bottom: '16px',
        left: '16px',
        zIndex: 1000,
        backgroundColor: '#FFFFFF',
        border: '1px solid #E2E8F0',
        borderRadius: '12px',
        padding: '20px',
        boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
        maxWidth: '280px',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
      }}>
        <div style={{ 
          fontSize: '14px',
          fontWeight: '600', 
          marginBottom: '16px', 
          color: '#0F172A',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <span style={{ fontSize: '16px' }}>🧠</span>
          Mental Model Types
        </div>
        
        {[
          { color: '#DC2626', label: 'Theme', count: '70' },
          { color: '#059669', label: 'Value Framework', count: '168' },
          { color: '#2563EB', label: 'Cognitive Tensions', count: '132' },
          { color: '#7C3AED', label: 'Decision Architecture', count: '105' },
          { color: '#EA580C', label: 'Adaptive Core', count: '88' },
          { color: '#DB2777', label: 'Energy Patterns', count: '36' },
          { color: '#64748B', label: 'Uncategorized', count: '14' }
        ].map((item, index) => (
          <div key={index} style={{ 
            display: 'flex', 
            alignItems: 'center', 
            marginBottom: index === 6 ? '0' : '10px',
            gap: '12px'
          }}>
            <div style={{ 
              width: '12px', 
              height: '12px', 
              backgroundColor: item.color, 
              borderRadius: '50%',
              flexShrink: 0
            }}></div>
            <span style={{ 
              fontSize: '13px',
              color: '#475569',
              flex: 1
            }}>
              {item.label}
            </span>
            <span style={{
              fontSize: '12px',
              color: '#94A3B8',
              fontWeight: '500',
              backgroundColor: '#F1F5F9',
              padding: '2px 6px',
              borderRadius: '4px',
              minWidth: '24px',
              textAlign: 'center'
            }}>
              {item.count}
            </span>
          </div>
        ))}
      </div>

      <NVL
        ref={nvlRef}
        nodes={graphData.nodes}
        rels={graphData.relationships}
        nvlOptions={{
          layout: 'force-directed',
          initialZoom: 1,
          allowDynamicMinZoom: true
        }}
        mouseEventCallbacks={mouseEventCallbacks}
        nvlCallbacks={nvlCallbacks}
      />
    </div>
  );
}

export default GraphView;