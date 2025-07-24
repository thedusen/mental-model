import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import GraphView from './components/GraphView';
import ChatPanel from './components/ChatPanel';
import NodeDetailsPanel from './components/NodeDetailsPanel';
import NodeTypesPanel from './components/NodeTypesPanel';
import SearchBar from './components/SearchBar';
import IntroductionPanel from './components/IntroductionPanel';
import LeftSidebar from './components/LeftSidebar';

function App() {
  console.log('App component rendering...');
  const [selectedNode, setSelectedNode] = useState(null);
  // New state for managing chat context - separate from selected node for viewing
  const [chatContextNode, setChatContextNode] = useState(null);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [nodeFilters, setNodeFilters] = useState([]);
  const [isChatFullscreen, setIsChatFullscreen] = useState(false);
  // Introduction panel state
  const [showIntroPanel, setShowIntroPanel] = useState(true);
  const [hasClickedNode, setHasClickedNode] = useState(false);
  
  // Left sidebar state - start open by default
  const [isLeftSidebarCollapsed, setIsLeftSidebarCollapsed] = useState(false);
  const [currentChatSession, setCurrentChatSession] = useState(null);
  
  // Chat input state for passing messages from intro panel to chat
  const [chatInput, setChatInput] = useState('');
  
  // Authentication trigger ref - function to trigger auth sidebar
  const authTriggerRef = useRef(null);
  
  // Chat message handling - this will be passed to ChatPanel
  const handleAddChatMessage = (message) => {
    // Hide intro panel on first interaction
    if (!hasClickedNode) {
      setHasClickedNode(true);
      setShowIntroPanel(false);
    }
    
    // Set the message and focus chat (ChatPanel will handle this via props)
    setChatInput(message);
    
    // Focus the chat input after a brief delay
    setTimeout(() => {
      const chatTextarea = document.querySelector('.chat-panel textarea');
      if (chatTextarea) {
        chatTextarea.focus();
        chatTextarea.setSelectionRange(chatTextarea.value.length, chatTextarea.value.length);
      }
    }, 100);
  };
  
  // Search-related state
  const [searchResults, setSearchResults] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchLoading, setIsSearchLoading] = useState(false);
  const [isSearchResultsVisible, setIsSearchResultsVisible] = useState(false);
  const [searchExecutionTime, setSearchExecutionTime] = useState(0);
  
  // Graph filtering state
  const [graphFilterMode, setGraphFilterMode] = useState(null); // null | 'node-only' | 'node-with-connections'
  const [filteredNodeId, setFilteredNodeId] = useState(null);
  const [filteredGraphData, setFilteredGraphData] = useState(null);
  const [isLoadingSubgraph, setIsLoadingSubgraph] = useState(false);
  
  // Refs
  const graphViewRef = useRef(null);
  const chatPanelRef = useRef(null);
  
  // API URL configuration with validation
  const API_URL = (() => {
    const envUrl = process.env.REACT_APP_API_URL;
    console.log('Environment API_URL:', envUrl);
    
    if (!envUrl || envUrl.trim() === '') {
      console.warn('REACT_APP_API_URL not set, using localhost fallback');
      return 'http://localhost:8000';
    }
    
    try {
      new URL(envUrl);
      return envUrl;
    } catch (error) {
      console.error('Invalid REACT_APP_API_URL:', envUrl, error);
      throw new Error(`Invalid API URL configuration: ${envUrl}`);
    }
  })();


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

  // Chat session handlers for left sidebar
  const handleSessionSelect = (session, messages) => {
    setCurrentChatSession(session);
    // Pass to ChatPanel via ref or prop
    if (chatPanelRef.current && chatPanelRef.current.handleSessionSelect) {
      chatPanelRef.current.handleSessionSelect(session, messages);
    }
  };

  const handleNewChat = () => {
    setCurrentChatSession(null);
    // Clear chat panel
    if (chatPanelRef.current && chatPanelRef.current.handleNewChat) {
      chatPanelRef.current.handleNewChat();
    }
    
    // Focus chat input
    setTimeout(() => {
      const chatInput = document.querySelector('.chat-panel textarea');
      if (chatInput) {
        chatInput.focus();
      }
    }, 100);
  };

  // Search handlers
  const handleSearch = async (query) => {
    if (!query || query.length < 2) return;
    
    setIsSearchLoading(true);
    setSearchQuery(query);
    setIsSearchResultsVisible(true);
    
    try {
      const response = await fetch(`${API_URL}/api/search?q=${encodeURIComponent(query)}&limit=10&threshold=0.3`);
      
      if (!response.ok) {
        throw new Error(`Search failed: ${response.status}`);
      }
      
      const data = await response.json();
      setSearchResults(data.results);
      setSearchExecutionTime(data.execution_time_ms);
      
      // Auto-zoom to search results if there are any
      if (data.results.length > 0) {
        setTimeout(() => {
          if (graphViewRef.current) {
            graphViewRef.current.zoomToSearchResults(data.results);
          }
        }, 100);
      }
      
    } catch (error) {
      console.error('Search error:', error);
      setSearchResults([]);
      setSearchExecutionTime(0);
      // Could add user notification here
    } finally {
      setIsSearchLoading(false);
    }
  };

  const handleSearchClear = () => {
    setSearchResults([]);
    setSearchQuery('');
    setIsSearchResultsVisible(false);
    setSearchExecutionTime(0);
    
    // Reset graph to full view when clearing search
    if (graphFilterMode) {
      handleClearGraphFilter();
    }
  };

  // Graph filtering functions
  const handleIsolateNode = async (nodeId, includeConnections = true) => {
    if (!nodeId) return;
    
    setIsLoadingSubgraph(true);
    try {
      const response = await fetch(
        `${API_URL}/api/graph/subgraph/${encodeURIComponent(nodeId)}?include_connections=${includeConnections}`
      );
      
      if (!response.ok) {
        throw new Error(`Failed to load subgraph: ${response.status}`);
      }
      
      const subgraphData = await response.json();
      setFilteredGraphData(subgraphData);
      setFilteredNodeId(nodeId);
      setGraphFilterMode(includeConnections ? 'node-with-connections' : 'node-only');
      
      console.log(`Isolated node ${nodeId}:`, subgraphData);
      
      // Zoom to the subgraph after a brief delay
      setTimeout(() => {
        if (graphViewRef.current) {
          graphViewRef.current.fitToScreen();
        }
      }, 100);
      
    } catch (error) {
      console.error('Error isolating node:', error);
      // Could add user notification here
    } finally {
      setIsLoadingSubgraph(false);
    }
  };

  const handleClearGraphFilter = () => {
    setGraphFilterMode(null);
    setFilteredNodeId(null);
    setFilteredGraphData(null);
    
    // Fit to full graph after a brief delay
    setTimeout(() => {
      if (graphViewRef.current) {
        graphViewRef.current.fitToScreen();
      }
    }, 100);
  };

  const handleSearchResultClick = (result) => {
    // Hide intro panel on first interaction
    if (!hasClickedNode) {
      setHasClickedNode(true);
      setShowIntroPanel(false);
    }
    
    // Jump to the specific node without isolating it first
    if (graphViewRef.current && graphViewRef.current.jumpToNode) {
      graphViewRef.current.jumpToNode(result.id);
    }
    
    // Clear search results to better see the node jump (but delay it more)
    setTimeout(() => {
      handleSearchClear();
      
      // Then select the node after search is cleared and jump is complete
      setTimeout(() => {
        setSelectedNode({
          id: result.id,
          properties: {
            name: result.id,
            description: result.description,
            category: result.type,
            theme: result.theme,
            searchScore: result.score
          }
        });
      }, 100);
    }, 150);
  };

  // New function for search result isolation
  const handleSearchResultIsolate = (result, includeConnections = true) => {
    // Also select the node
    handleSearchResultClick(result);
    
    // Then isolate it
    handleIsolateNode(result.id, includeConnections);
  };


  // Keyboard navigation for accessibility
  useEffect(() => {
    const handleKeyDown = (event) => {
      // Escape key to clear graph filter, search results, or deselect node
      if (event.key === 'Escape') {
        if (isSearchResultsVisible) {
          event.preventDefault();
          handleSearchClear();
        } else if (graphFilterMode) {
          event.preventDefault();
          handleClearGraphFilter();
        } else if (selectedNode) {
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
  }, [selectedNode, isSearchResultsVisible, graphFilterMode, handleSearchClear, handleClearGraphFilter, handleDeselectNode]);

  // Click outside handler for search results
  useEffect(() => {
    const handleClickOutside = (event) => {
      // Check if click is outside search area
      const searchBar = document.querySelector('.search-bar');
      const searchResults = document.querySelector('.search-results-overlay');
      
      if (isSearchResultsVisible && searchBar && searchResults) {
        const isClickInsideSearch = searchBar.contains(event.target) || searchResults.contains(event.target);
        
        if (!isClickInsideSearch) {
          handleSearchClear();
        }
      }
    };

    if (isSearchResultsVisible) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isSearchResultsVisible, handleSearchClear]);

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
        
        {/* Left Sidebar for Chat History and User Profile */}
        <LeftSidebar 
          onSessionSelect={handleSessionSelect}
          currentSessionId={currentChatSession?.id}
          onNewChat={handleNewChat}
          isCollapsed={isLeftSidebarCollapsed}
          onToggleCollapse={() => setIsLeftSidebarCollapsed(!isLeftSidebarCollapsed)}
          onAuthTrigger={(triggerFn) => { authTriggerRef.current = triggerFn; }}
        />
        
        <main className={`main-content ${isLeftSidebarCollapsed ? 'sidebar-collapsed' : ''}`} id="main-content" role="main">
          {/* Search Bar */}
          <div className="search-header">
            <SearchBar 
              onSearch={handleSearch}
              onClear={handleSearchClear}
              isLoading={isSearchLoading}
              searchResults={searchResults}
              searchQuery={searchQuery}
              searchExecutionTime={searchExecutionTime}
              isSearchResultsVisible={isSearchResultsVisible}
              onResultClick={handleSearchResultClick}
              onResultIsolate={handleSearchResultIsolate}
              graphFilterMode={graphFilterMode}
              onClearGraphFilter={handleClearGraphFilter}
            />
          </div>
          
          <div className="graph-container">
            <div className="graph-view-area">
              <NodeTypesPanel onFilterChange={setNodeFilters} />
              <GraphView 
                ref={graphViewRef}
                onNodeSelect={(node) => {
                  setSelectedNode(node);
                  if (!hasClickedNode) {
                    setHasClickedNode(true);
                    setShowIntroPanel(false);
                  }
                }}
                onCanvasClick={handleDeselectNode}
                chatContextNode={chatContextNode}
                selectedNode={selectedNode}
                searchResults={searchResults}
                filters={nodeFilters}
                filteredGraphData={filteredGraphData}
                graphFilterMode={graphFilterMode}
                filteredNodeId={filteredNodeId}
                onClearGraphFilter={handleClearGraphFilter}
                isLoadingSubgraph={isLoadingSubgraph}
              />
            </div>
            <div className={`chat-container ${isChatFullscreen ? 'fullscreen' : ''}`}>
              <ChatPanel 
                ref={chatPanelRef}
                selectedNode={selectedNode}
                chatContextNode={chatContextNode}
                onClearChatContext={handleClearChatContext}
                onFullscreenChange={setIsChatFullscreen}
                externalInput={chatInput}
                onExternalInputReceived={() => setChatInput('')}
                onSessionChange={setCurrentChatSession}
                onOpenSidebarAuth={() => authTriggerRef.current && authTriggerRef.current()}
              />
            </div>
          </div>
        </main>
        
        <aside className={`sidebar ${isSidebarCollapsed ? 'collapsed' : ''}`} role="complementary" aria-label="Node details">
          {showIntroPanel ? (
            <IntroductionPanel 
              isVisible={showIntroPanel}
              onClose={() => setShowIntroPanel(false)}
              onAddChatMessage={handleAddChatMessage}
            />
          ) : (
            <NodeDetailsPanel
              selectedNode={selectedNode}
              chatContextNode={chatContextNode}
              onSetChatContext={handleSetChatContext}
              isCollapsed={isSidebarCollapsed}
              onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
            />
          )}
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