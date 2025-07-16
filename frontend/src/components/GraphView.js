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

      // Transform data for NVL
      const nvlNodes = nodes.map(node => ({
        id: node.id,
        labels: [node.type],
        properties: {
          name: node.label,
          description: node.description
        },
        caption: node.label
      }));

      const nvlRelationships = edges.map((edge, idx) => ({
        id: `rel-${idx}`,
        from: edge.from,
        to: edge.to,
        caption: edge.label
      }));

      setGraphData({
        nodes: nvlNodes,
        relationships: nvlRelationships
      });
    } catch (error) {
      console.error('Error loading graph:', error);
    }
  };

  const handleNodeClick = (nodes) => {
    if (nodes.length > 0) {
      const nodeId = nodes[0];
      const node = graphData.nodes.find(n => n.id === nodeId);
      onNodeSelect(node);
    }
  };

  // Node styling based on type
  const nodeStyler = (node) => {
    const typeColors = {
      'Concept': '#4CAF50',
      'Principle': '#2196F3',
      'Metric': '#FF9800',
      'Example': '#9C27B0'
    };

    return {
      color: typeColors[node.labels[0]] || '#757575',
      size: 30,
      fontSize: 12
    };
  };

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <NVL
        ref={nvlRef}
        nodes={graphData.nodes}
        relationships={graphData.relationships}
        layout="force-directed"
        nodeStyler={nodeStyler}
        onNodeClick={handleNodeClick}
        mouseNavigation={true}
      />
    </div>
  );
}

export default GraphView;