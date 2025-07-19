import React, { useEffect, useRef, useState } from 'react';
import { InteractiveNvlWrapper as NVL } from '@neo4j-nvl/react';
import axios from 'axios';

function GraphView({ onNodeSelect }) {
  console.log('GraphView component rendering...');
  const [graphData, setGraphData] = useState({ nodes: [], relationships: [] });
  const [isLegendMinimized, setIsLegendMinimized] = useState(false);
  const [error, setError] = useState(null);
  const nvlRef = useRef(null);

  // Use environment variable for API URL, fallback to localhost for development
  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  useEffect(() => {
    console.log('GraphView useEffect running...');
    loadGraph();
  }, []);

  const loadGraph = async () => {
    console.log('Loading graph data...');
    try {
      const response = await axios.get(`${API_URL}/api/graph`);
      console.log('API response:', response.data);
      const { nodes, edges } = response.data;

      console.log('Processing nodes:', nodes?.length, 'edges:', edges?.length);

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

        const baseSize = isTheme ? 35 : 20;
        const nodeColor = typeColors[node.type] || typeColors['Uncategorized'];
        
        return {
          id: node.id,
          caption: node.label,
          size: baseSize,
          color: nodeColor,
          fontSize: isTheme ? 14 : 11,
          font: {
            color: '#FFFFFF',
            strokeWidth: 0.3,
            strokeColor: '#1E293B',
            size: isTheme ? 14 : 11
          },
          type: 'circle',
          borderColor: nodeColor,
          borderWidth: isTheme ? 3 : 2,
          shadowEnabled: true,
          shadowColor: 'rgba(0, 0, 0, 0.2)',
          shadowBlur: 6,
          shadowOffsetX: 2,
          shadowOffsetY: 2,
          properties: {
            name: node.label,
            description: node.description,
            category: node.type,
            fullData: node
          }
        };
      });

      const nvlRels = edges.map((edge, idx) => ({
        id: `rel-${idx}`,
        from: edge.from,
        to: edge.to,
        caption: edge.label,
        color: '#94A3B8',       // Slate-400 for relationships
        width: 2,
        length: 150,
        arrows: 'to',
        arrowStrikethrough: false,
        font: {
          size: 10,
          color: '#64748B',      // Slate-500 for relationship labels
          strokeWidth: 0,
          align: 'middle'
        },
        smooth: {
          enabled: true,
          type: 'continuous',
          roundness: 0.2
        }
      }));

      console.log('Processed data:', { nodes: nvlNodes.length, relationships: nvlRels.length });
      setGraphData({ nodes: nvlNodes, relationships: nvlRels });
    } catch (error) {
      console.error('Error loading graph:', error);
      setError(error.message);
    }
  };

  const mouseEventCallbacks = {
    onNodeClick: (node) => {
      console.log('Node clicked:', node);
      if (onNodeSelect) {
        onNodeSelect(node);
      }
    }
  };

  const nvlCallbacks = {
    onLayoutComputed: (nodes, rels) => {
      console.log('Layout computed');
    }
  };

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

  const legendItems = [
    { color: '#DC2626', label: 'Theme', count: '70' },
    { color: '#059669', label: 'Value Framework', count: '168' },
    { color: '#2563EB', label: 'Cognitive Tensions', count: '132' },
    { color: '#7C3AED', label: 'Decision Architecture', count: '105' },
    { color: '#EA580C', label: 'Adaptive Core', count: '88' },
    { color: '#DB2777', label: 'Energy Patterns', count: '36' },
    { color: '#64748B', label: 'Uncategorized', count: '14' }
  ];

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

  console.log('Rendering GraphView with data:', graphData);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
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
          title="Zoom In"
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
          title="Zoom Out"
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

      {/* Enhanced Minimizable Legend */}
      <div style={{
        position: 'absolute',
        bottom: '16px',
        left: '16px',
        zIndex: 1000,
        backgroundColor: '#FFFFFF',
        border: '1px solid #E2E8F0',
        borderRadius: '16px',
        boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 10px 10px -5px rgb(0 0 0 / 0.04)',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
        overflow: 'hidden',
        transition: 'all 0.3s ease',
        backdropFilter: 'blur(8px)',
        backgroundColor: 'rgba(255, 255, 255, 0.95)'
      }}>
        {/* Legend Header */}
        <div 
          style={{ 
            padding: '16px 20px',
            borderBottom: isLegendMinimized ? 'none' : '1px solid #F1F5F9',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: 'pointer',
            transition: 'all 0.2s ease'
          }}
          onClick={() => setIsLegendMinimized(!isLegendMinimized)}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = '#F8FAFC';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'transparent';
          }}
        >
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <span style={{ fontSize: '16px' }}>🧠</span>
            <span style={{
              fontSize: '14px',
              fontWeight: '600',
              color: '#0F172A'
            }}>
              Mental Model Types
            </span>
          </div>
          
          <button style={{
            background: 'none',
            border: 'none',
            fontSize: '12px',
            color: '#64748B',
            cursor: 'pointer',
            padding: '4px',
            borderRadius: '4px',
            transition: 'all 0.2s ease',
            transform: isLegendMinimized ? 'rotate(180deg)' : 'rotate(0deg)'
          }}>
            ▼
          </button>
        </div>
        
        {/* Legend Content */}
        {!isLegendMinimized && (
          <div style={{
            padding: '16px 20px'
          }}>
            {legendItems.map((item, index) => (
              <div key={index} style={{ 
                display: 'flex', 
                alignItems: 'center', 
                marginBottom: index === legendItems.length - 1 ? '0' : '12px',
                gap: '12px',
                padding: '4px 0',
                borderRadius: '6px',
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#F8FAFC';
                e.currentTarget.style.transform = 'translateX(2px)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.transform = 'translateX(0)';
              }}
              >
                <div style={{ 
                  width: '12px', 
                  height: '12px', 
                  backgroundColor: item.color, 
                  borderRadius: '50%',
                  flexShrink: 0,
                  boxShadow: `0 0 0 2px ${item.color}20`
                }}></div>
                <span style={{ 
                  fontSize: '13px',
                  color: '#475569',
                  flex: 1,
                  fontWeight: '500'
                }}>
                  {item.label}
                </span>
                <span style={{
                  fontSize: '11px',
                  color: '#64748B',
                  fontWeight: '600',
                  backgroundColor: '#F1F5F9',
                  padding: '2px 8px',
                  borderRadius: '6px',
                  minWidth: '28px',
                  textAlign: 'center',
                  border: '1px solid #E2E8F0'
                }}>
                  {item.count}
                </span>
              </div>
            ))}
          </div>
        )}
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