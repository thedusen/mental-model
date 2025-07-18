import React, { useState } from 'react';
import './App.css';
import GraphViewD3 from './components/GraphViewD3';
import ChatPanel from './components/ChatPanel';
import NodeDetailsPanel from './components/NodeDetailsPanel';
import NodeTypesPanel from './components/NodeTypesPanel';

function App() {
  console.log('App component rendering...');
  const [selectedNode, setSelectedNode] = useState(null);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [nodeFilters, setNodeFilters] = useState([]);

  console.log('App state:', { selectedNode, isSidebarCollapsed });

  try {
    return (
      <div className="app">
        <div className="main-content">
          <div className="graph-container">
            <NodeTypesPanel onFilterChange={setNodeFilters} />
            <GraphViewD3 
              onNodeSelect={setSelectedNode} 
              filters={nodeFilters}
            />
          </div>
          <div className="chat-container">
            <ChatPanel selectedNode={selectedNode} />
          </div>
        </div>
        <div className={`sidebar ${isSidebarCollapsed ? 'collapsed' : ''}`}>
          <NodeDetailsPanel
            selectedNode={selectedNode}
            isCollapsed={isSidebarCollapsed}
            onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
          />
        </div>
      </div>
    );
  } catch (error) {
    console.error('Error in App component:', error);
    return (
      <div style={{ padding: '20px', color: 'red' }}>
        <h1>Error</h1>
        <p>Something went wrong: {error.message}</p>
      </div>
    );
  }
}

export default App;