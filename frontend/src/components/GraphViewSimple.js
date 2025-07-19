import React, { useEffect, useState } from 'react';
import axios from 'axios';

// Use environment variable for API URL, fallback to localhost for development
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function GraphViewSimple({ onNodeSelect }) {
  console.log('GraphViewSimple component rendering...');
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [error, setError] = useState(null);
  const [isLegendMinimized, setIsLegendMinimized] = useState(false);

  useEffect(() => {
    console.log('GraphViewSimple useEffect running...');
    loadGraph();
  }, []);

  const loadGraph = async () => {
    console.log('Loading graph data...');
    try {
      const response = await axios.get(`${API_URL}/api/graph`);
      console.log('API response:', response.data);
      setGraphData(response.data);
    } catch (error) {
      console.error('Error loading graph:', error);
      setError(error.message);
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

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', backgroundColor: '#FAFAFA' }}>
      {/* Simple graph placeholder */}
      <div style={{ 
        padding: '40px', 
        textAlign: 'center', 
        height: '100%', 
        display: 'flex', 
        flexDirection: 'column', 
        justifyContent: 'center',
        alignItems: 'center'
      }}>
        <h2 style={{ color: '#0F172A', marginBottom: '20px' }}>Graph Data Loaded Successfully!</h2>
        <p style={{ color: '#64748B', marginBottom: '20px' }}>
          Nodes: {graphData.nodes?.length || 0} | Edges: {graphData.edges?.length || 0}
        </p>
        <div style={{ 
          backgroundColor: '#FFFFFF', 
          padding: '20px', 
          borderRadius: '8px', 
          border: '1px solid #E2E8F0',
          maxWidth: '600px',
          maxHeight: '200px',
          overflow: 'auto'
        }}>
          <h4>Sample Nodes:</h4>
          {graphData.nodes?.slice(0, 5).map((node, idx) => (
            <div key={idx} style={{ margin: '5px 0', fontSize: '12px' }}>
              <strong>{node.label}</strong> ({node.type})
            </div>
          ))}
        </div>
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
              }}>
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
    </div>
  );
}

export default GraphViewSimple; 