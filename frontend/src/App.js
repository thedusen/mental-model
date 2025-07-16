import React, { useState } from 'react';
import './App.css';
import GraphView from './components/GraphView';
import ChatPanel from './components/ChatPanel';

function App() {
  const [selectedNode, setSelectedNode] = useState(null);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Mental Model Knowledge Graph</h1>
      </header>
      <div className="app-content">
        <div className="graph-container">
          <GraphView onNodeSelect={setSelectedNode} />
        </div>
        <div className="chat-container">
          <ChatPanel selectedNode={selectedNode} />
        </div>
      </div>
    </div>
  );
}

export default App;