import React, { useState, useEffect } from 'react';
import './App.css';
import GraphViewD3 from './components/GraphViewD3';
import ChatPanel from './components/ChatPanel';
import NodeDetailsPanel from './components/NodeDetailsPanel';
import NodeTypesPanel from './components/NodeTypesPanel';

function App() {
  console.log('App component rendering...');
  const [selectedNode, setSelectedNode] = useState(null);
  // New state for managing chat context - separate from selected node for viewing
  const [chatContextNode, setChatContextNode] = useState(null);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [nodeFilters, setNodeFilters] = useState([]);
  const [isChatFullscreen, setIsChatFullscreen] = useState(false);

  console.log('App state:', { selectedNode, chatContextNode, isSidebarCollapsed });

  // Handler to deselect the currently selected node (triggered by canvas clicks)
  const handleDeselectNode = () => {
    setSelectedNode(null);
  };

  // Handler to set a node as the active chat context
  const handleSetChatContext = (node) => {
    setChatContextNode(node);
    // Announce to screen readers
    const announcement = `Node "${node.properties?.name || node.name || 'Unknown'}" added to chat context`;
    const liveRegion = document.getElementById('chat-context-announcements');
    if (liveRegion) {
      liveRegion.textContent = announcement;
    }
  };

  // Handler to clear the chat context
  const handleClearChatContext = () => {
    const prevNodeName = chatContextNode?.properties?.name || chatContextNode?.name || 'Unknown';
    setChatContextNode(null);
    // Announce to screen readers
    const announcement = `Node "${prevNodeName}" removed from chat context`;
    const liveRegion = document.getElementById('chat-context-announcements');
    if (liveRegion) {
      liveRegion.textContent = announcement;
    }
    
    // Focus management: move focus to chat input for smooth workflow
    setTimeout(() => {
      const chatInput = document.querySelector('.chat-panel textarea');
      if (chatInput) {
        chatInput.focus();
      }
    }, 100);
  };

  // Keyboard navigation for accessibility
  useEffect(() => {
    const handleKeyDown = (event) => {
      // Escape key to deselect node
      if (event.key === 'Escape') {
        if (selectedNode) {
          event.preventDefault();
          handleDeselectNode();
        }
      }
      // Alt + 1: Focus on node types panel
      else if (event.altKey && event.key === '1') {
        event.preventDefault();
        const nodeTypesPanel = document.querySelector('.node-types-panel');
        if (nodeTypesPanel) {
          const firstInteractive = nodeTypesPanel.querySelector('button, input, select, textarea, [tabindex]:not([tabindex="-1"])');
          if (firstInteractive) firstInteractive.focus();
        }
      }
      // Alt + 2: Focus on graph (not directly focusable, but we can focus the zoom controls)
      else if (event.altKey && event.key === '2') {
        event.preventDefault();
        const graphControls = document.querySelector('.graph-container button');
        if (graphControls) graphControls.focus();
      }
      // Alt + 3: Focus on chat panel
      else if (event.altKey && event.key === '3') {
        event.preventDefault();
        const chatInput = document.querySelector('.chat-panel textarea');
        if (chatInput) chatInput.focus();
      }
      // Alt + 4: Focus on details panel
      else if (event.altKey && event.key === '4') {
        event.preventDefault();
        const detailsPanel = document.querySelector('.node-details-panel');
        if (detailsPanel) {
          const firstInteractive = detailsPanel.querySelector('button, input, select, textarea, [tabindex]:not([tabindex="-1"])');
          if (firstInteractive) firstInteractive.focus();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [selectedNode]);

  try {
    return (
      <div className="app" role="application" aria-label="Mental Model Knowledge Graph">
        {/* Skip link for keyboard users */}
        <a href="#main-content" className="sr-only">Skip to main content</a>
        
        {/* Hidden live region for chat context announcements */}
        <div 
          id="chat-context-announcements" 
          className="sr-only" 
          aria-live="polite" 
          aria-atomic="false"
        ></div>
        
        <main className="main-content" id="main-content" role="main">
          <div className="graph-container">
            <NodeTypesPanel onFilterChange={setNodeFilters} />
            <GraphViewD3 
              onNodeSelect={setSelectedNode}
              onCanvasClick={handleDeselectNode}
              chatContextNode={chatContextNode}
              filters={nodeFilters}
            />
            <div className={`chat-container ${isChatFullscreen ? 'fullscreen' : ''}`}>
              <ChatPanel 
                selectedNode={selectedNode}
                chatContextNode={chatContextNode}
                onClearChatContext={handleClearChatContext}
                onFullscreenChange={setIsChatFullscreen}
              />
            </div>
          </div>
        </main>
        <aside className={`sidebar ${isSidebarCollapsed ? 'collapsed' : ''}`} role="complementary" aria-label="Node details">
          <NodeDetailsPanel
            selectedNode={selectedNode}
            chatContextNode={chatContextNode}
            onSetChatContext={handleSetChatContext}
            isCollapsed={isSidebarCollapsed}
            onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
          />
        </aside>
      </div>
    );
  } catch (error) {
    console.error('Error in App component:', error);
    return (
      <div style={{ padding: '20px', color: 'red' }} role="alert">
        <h1>Error</h1>
        <p>Something went wrong: {error.message}</p>
      </div>
    );
  }
}

export default App;