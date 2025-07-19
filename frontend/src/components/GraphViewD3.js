import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import axios from 'axios';

// Use environment variable for API URL, fallback to localhost for development
let API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Ensure the API URL has a protocol
if (API_URL && !API_URL.startsWith('http://') && !API_URL.startsWith('https://')) {
  API_URL = `https://${API_URL}`;
}

// Debug logging
console.log('API_URL configured as:', API_URL);
console.log('Environment variables:', {
  NODE_ENV: process.env.NODE_ENV,
  REACT_APP_API_URL: process.env.REACT_APP_API_URL
});

// A helper function to wrap text into multiple lines inside an SVG
function wrap(text, width) {
  text.each(function () {
    const textEl = d3.select(this);
    const words = textEl.text().split(/\s+/).reverse();
    let word;
    let line = [];
    let lineNumber = 0;
    const lineHeight = 1.1; // ems
    
    textEl.text(null); // Clear previous text

    let tspan = textEl.append('tspan').attr('x', 0).attr('dy', '0em');
    
    while ((word = words.pop())) {
      line.push(word);
      tspan.text(line.join(' '));
      if (tspan.node().getComputedTextLength() > width && line.length > 1) {
        line.pop();
        tspan.text(line.join(' '));
        line = [word];
        // For subsequent lines, create a new tspan and set dy for line break
        tspan = textEl.append('tspan').attr('x', 0).attr('dy', lineHeight + 'em').text(word);
      }
    }

    // After wrapping, we need to vertically center the text block.
    const tspans = textEl.selectAll('tspan');
    const lineCount = tspans.size();
    // Shift the entire text block up by half of its total height.
    textEl.attr('y', `-${(lineCount - 1) * 0.4 * lineHeight}em`);
  });
}


function GraphViewD3({ onNodeSelect }) {
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [isLegendMinimized, setIsLegendMinimized] = useState(false);
  const [error, setError] = useState(null);
  const svgRef = useRef(null);
  const simulationRef = useRef(null);
  const zoomRef = useRef(null);

  useEffect(() => {
    loadGraph();
  }, []);

  useEffect(() => {
    if (graphData.nodes.length > 0 && svgRef.current) {
      try {
        initializeGraph();
      } catch (error) {
        console.error('Error initializing graph:', error);
        setError(`Graph initialization failed: ${error.message}`);
      }
    }
    return () => {
      if (simulationRef.current) {
        simulationRef.current.stop();
      }
    };
  }, [graphData]);

  const loadGraph = async () => {
    try {
      console.log('Loading graph from:', `${API_URL}/api/graph`);
      const response = await axios.get(`${API_URL}/api/graph`);
      console.log('API response received:', response);
      console.log('Response data:', response.data);
      
      // Validate the structure of the response
      if (!response.data || !response.data.nodes || !response.data.edges) {
        console.error('Invalid response structure:', response.data);
        throw new Error(`Invalid graph data structure received from API. Received: ${JSON.stringify(response.data)}`);
      }
      
      console.log('Graph data loaded successfully:', response.data.nodes.length, 'nodes,', response.data.edges.length, 'edges');
      setGraphData(response.data);
    } catch (error) {
      console.error('Error loading graph:', error);
      console.error('Error details:', {
        message: error.message,
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data
      });
      setError(error.message);
    }
  };

  const getNodeColor = (nodeType) => {
    const typeColors = {
      'Theme': '#F4B8A2',                   // Light Salmon
      'VALUE FRAMEWORK': '#A3D9D2',          // Teal
      'COGNITIVE TENSIONS': '#A9C7E8',       // Soft Blue
      'DECISION ARCHITECTURE': '#C3B4E5',    // Lavender
      'ADAPTIVE CORE': '#F9D6B3',           // Apricot
      'ENERGY PATTERNS': '#E9C3E1',         // Light Magenta
      'Uncategorized': '#E0E0E0'             // Light Gray
    };
    return typeColors[nodeType] || typeColors['Uncategorized'];
  };

  const initializeGraph = () => {
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove(); // Clear previous render

    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;

    const container = svg.append('g').attr('class', 'graph-container');
    
    const zoom = d3.zoom()
      .scaleExtent([0.1, 8])
      .on('zoom', (event) => {
        container.attr('transform', event.transform);
      });

    svg.call(zoom);
    zoomRef.current = zoom;

    const validNodes = graphData.nodes.filter(node => node && node.id != null);
    const nodeIds = new Set(validNodes.map(n => n.id));
    
    const validEdges = graphData.edges
      .filter(edge => edge.from && edge.to && nodeIds.has(edge.from) && nodeIds.has(edge.to))
      .map(edge => ({ source: edge.from, target: edge.to, label: edge.label }));

    // Dynamically calculate node radius based on its type initially
    validNodes.forEach(node => {
      const nodeType = node.properties ? node.properties.type : node.type;
      node.radius = nodeType === 'Theme' ? 50 : 30; // Initial radius
    });

    const simulation = d3.forceSimulation(validNodes)
      .force('link', d3.forceLink(validEdges).id(d => d.id).distance(120).strength(0.5))
      .force('charge', d3.forceManyBody().strength(-500))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collide', d3.forceCollide().radius(d => d.radius + 5).strength(0.8));

    simulationRef.current = simulation;

    const defs = svg.append('defs');
    
    defs.append('marker')
      .attr('id', 'arrowhead')
      .attr('viewBox', '-0 -5 10 10')
      .attr('refX', 23)
      .attr('refY', 0)
      .attr('orient', 'auto')
      .attr('markerWidth', 5)
      .attr('markerHeight', 5)
      .attr('xoverflow', 'visible')
      .append('svg:path')
      .attr('d', 'M 0,-5 L 10 ,0 L 0,5')
      .attr('fill', '#94a3b8')
      .style('stroke', 'none');

    // Manually define the color scale for gradients
    const colorScale = {
      'Theme': '#F4B8A2',
      'VALUE FRAMEWORK': '#A3D9D2',
      'COGNITIVE TENSIONS': '#A9C7E8',
      'DECISION ARCHITECTURE': '#C3B4E5',
      'ADAPTIVE CORE': '#F9D6B3',
      'ENERGY PATTERNS': '#E9C3E1',
      'Uncategorized': '#E0E0E0'
    };

    // Create a radial gradient for each node type for a more 3D effect
    Object.keys(colorScale).forEach(type => {
      const color = colorScale[type];
      const gradient = defs.append('radialGradient')
        .attr('id', `gradient-${type.replace(/\s+/g, '-')}`)
        .attr('cx', '30%')
        .attr('cy', '30%');

      gradient.append('stop')
        .attr('offset', '0%')
        .attr('stop-color', d3.color(color).brighter(0.3));
      
      gradient.append('stop')
        .attr('offset', '100%')
        .attr('stop-color', color);
    });

    const links = container.append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(validEdges)
      .enter().append('line')
      .attr('class', 'link')
      .attr('stroke', '#cbd5e1')
      .attr('stroke-width', 1.5)
      .attr('marker-end', 'url(#arrowhead)');

    const nodeGroups = container.append('g')
      .attr('class', 'nodes')
      .selectAll('.node-group')
      .data(validNodes)
      .enter().append('g')
      .attr('class', 'node-group')
      .style('cursor', 'pointer')
      .call(drag(simulation))
      .on('click', function(event, d) {
        onNodeSelect(d);
        // Highlight selected node
        nodeGroups.classed('selected', n => n.id === d.id);
      })
      .on('mouseover', function(event, d) {
        // No longer needed with persistent labels
      })
      .on('mouseout', function(event, d) {
        // No longer needed with persistent labels
      });

    nodeGroups.append('circle')
      .attr('class', 'node-circle')
      .attr('r', d => d.radius)
      .attr('fill', d => `url(#gradient-${(d.properties ? d.properties.type : d.type).replace(/\s+/g, '-')})`)
      .attr('stroke', d => d3.color(getNodeColor(d.properties ? d.properties.type : d.type)).darker(0.4))
      .attr('stroke-width', 1.5);

    // Add text labels to be placed inside the circles
    const nodeLabels = nodeGroups.append('text')
      .attr('class', 'node-label-inner')
      .attr('text-anchor', 'middle')
      .style('font-family', 'Inter, sans-serif')
      .style('font-weight', '600')
      .style('fill', '#1e293b')
      .style('pointer-events', 'none')
      .style('font-size', d => (d.properties ? d.properties.type : d.type) === 'Theme' ? '14px' : '12px')
      .text(d => (d.properties ? d.properties.name : d.name) || d.label)
      .call(wrap, 100); // Call the wrap function with a max width

    // After wrapping, dynamically update the radius of each node to fit the text
    nodeGroups.each(function(d) {
      const textBBox = d3.select(this).select('text').node().getBBox();
      const padding = 15;
      d.radius = Math.max(d.radius, Math.sqrt(Math.pow(textBBox.width, 2) + Math.pow(textBBox.height, 2)) / 2 + padding);
    });

    // Update the circle radius with a smooth transition
    nodeGroups.select('.node-circle')
      .transition().duration(750)
      .attr('r', d => d.radius);
    
    // Update the collision force with the final dynamic radii
    simulation.force('collide', d3.forceCollide().radius(d => d.radius + 5).strength(0.8));
    simulation.alpha(0.3).restart();

    simulation.on('tick', () => {
      // Update link positions
      links
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => {
          const dx = d.target.x - d.source.x;
          const dy = d.target.y - d.source.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const ratio = (dist - d.target.radius - 5) / dist; // -5 for arrowhead
          return d.source.x + dx * ratio;
        })
        .attr('y2', d => {
          const dx = d.target.x - d.source.x;
          const dy = d.target.y - d.source.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const ratio = (dist - d.target.radius - 5) / dist;
          return d.source.y + dy * ratio;
        });
      
      nodeGroups.attr('transform', d => `translate(${d.x},${d.y})`);
    });
  };

  const drag = (simulation) => {
    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }
    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }
    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }
    return d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended);
  }

  const handleZoomIn = () => {
    if (zoomRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(300)
        .call(zoomRef.current.scaleBy, 1.5);
    }
  };

  const handleZoomOut = () => {
    if (zoomRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(300)
        .call(zoomRef.current.scaleBy, 1 / 1.5);
    }
  };

  const legendItems = [
    { color: '#F4B8A2', label: 'Theme', count: '70' },              // Light Salmon - matches graph gradient base
    { color: '#A3D9D2', label: 'Value Framework', count: '168' },   // Teal - matches graph gradient base
    { color: '#A9C7E8', label: 'Cognitive Tensions', count: '132' }, // Soft Blue - matches graph gradient base
    { color: '#C3B4E5', label: 'Decision Architecture', count: '105' }, // Lavender - matches graph gradient base
    { color: '#F9D6B3', label: 'Adaptive Core', count: '88' },      // Apricot - matches graph gradient base
    { color: '#E9C3E1', label: 'Energy Patterns', count: '36' },    // Light Magenta - matches graph gradient base
    { color: '#E0E0E0', label: 'Uncategorized', count: '14' }       // Light Gray - matches graph gradient base
  ];

  if (error) {
    return (
      <div style={{ 
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100%',
        width: '100%',
        position: 'absolute',
        top: 0,
        left: 0,
        zIndex: 2000,
        backgroundColor: 'rgba(255, 255, 255, 0.95)'
      }}>
        <div style={{ 
          padding: '32px', 
          color: '#DC2626', 
          backgroundColor: '#FEF2F2', 
          border: '1px solid #FECACA', 
          borderRadius: '16px', 
          maxWidth: '500px',
          width: '90%',
          textAlign: 'center',
          boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 10px 10px -5px rgb(0 0 0 / 0.04)'
        }}>
          <h3 style={{ margin: '0 0 16px 0', fontWeight: '600', fontSize: '18px' }}>Graph Loading Error</h3>
          <p style={{ margin: '0 0 24px 0', lineHeight: '1.5' }}>Failed to load graph data: {error}</p>
          <button 
            onClick={loadGraph} 
            style={{ 
              padding: '12px 24px', 
              backgroundColor: '#DC2626',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: '500',
              fontSize: '14px'
            }}
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', backgroundColor: '#FAFBFC' }}>
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
            boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
            transition: 'all 0.2s ease',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          title="Zoom In"
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
            boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
            transition: 'all 0.2s ease',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          title="Zoom Out"
        >
          －
        </button>
      </div>

      {/* Enhanced Legend */}
      <div style={{
        position: 'absolute',
        top: '16px',
        left: '16px',
        zIndex: 1000,
        backgroundColor: '#FFFFFF',
        borderRadius: '16px',
        boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
        border: '1px solid #E2E8F0',
        overflow: 'hidden',
        minWidth: '280px',
        maxWidth: '320px'
      }}>
        <div style={{
          padding: '16px 20px 12px 20px',
          borderBottom: isLegendMinimized ? 'none' : '1px solid #F1F5F9',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <h3 style={{ 
            margin: 0, 
            fontSize: '16px', 
            fontWeight: '600', 
            color: '#1E293B',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
          }}>
            Node Types
          </h3>
          <button
            onClick={() => setIsLegendMinimized(!isLegendMinimized)}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '4px',
              borderRadius: '6px',
              color: '#64748B',
              fontSize: '14px',
              transition: 'all 0.2s ease',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontWeight: '500'
            }}
            title={isLegendMinimized ? 'Expand' : 'Minimize'}
          >
            <span>{isLegendMinimized ? 'Show' : 'Hide'}</span>
            {isLegendMinimized ? '▼' : '▲'}
          </button>
        </div>
        
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
                  boxShadow: `0 0 0 2px ${item.color}20, 0 2px 4px -1px rgba(0, 0, 0, 0.2)`
                }}></div>
                <span style={{ 
                  fontSize: '13px',
                  color: '#475569',
                  flex: 1,
                  fontWeight: '500',
                  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
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

      <svg
        ref={svgRef}
        style={{ 
          width: '100%', 
          height: '100%',
          background: 'radial-gradient(ellipse at center, #FFFFFF 0%, #F8FAFC 100%)'
        }}
      />
    </div>
  );
}

export default GraphViewD3; 