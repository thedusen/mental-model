import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import { InteractiveNvlWrapper as NVL } from '@neo4j-nvl/react';
import axios from 'axios';
import LoadingSpinner from './LoadingSpinner';

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

const GraphView = React.forwardRef(({ 
  onNodeSelect, 
  onCanvasClick, 
  chatContextNode, 
  selectedNode = null,
  searchResults = [], 
  filters,
  filteredGraphData = null,
  graphFilterMode = null,
  filteredNodeId = null,
  onClearGraphFilter = null,
  isLoadingSubgraph = false
}, ref) => {
  console.log('GraphView render - searchResults:', searchResults);
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  // State to manage the legend's collapsed state
  const [isLegendMinimized, setIsLegendMinimized] = useState(false); 
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const nvlRef = useRef(null);
  
  // Use environment variable for API URL, fallback to localhost for development
  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  useEffect(() => {
    console.log('GraphViewD3 useEffect running...');
    loadGraph();
  }, []);

  const loadGraph = useCallback(async () => {
    console.log('Loading graph data...');
    setIsLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${API_URL}/api/graph`, {
        // Add timeout for better performance
        timeout: 10000,
        headers: {
          'Accept': 'application/json'
        }
      });
      console.log('API response:', response.data);
      const { nodes, edges } = response.data;
      console.log('Processing nodes:', nodes?.length, 'edges:', edges?.length);
      setGraphData({ nodes, edges });
    } catch (error) {
      console.error('Error loading graph:', error);
      setError(error.message);
    } finally {
      setIsLoading(false);
    }
  }, [API_URL]);

  // Memoize the type colors to avoid recreating on every render
  const typeColors = useMemo(() => ({
    'Theme': '#F4B8A2',
    'VALUE FRAMEWORK': '#A3D9D2',
    'COGNITIVE TENSIONS': '#A9C7E8',
    'DECISION ARCHITECTURE': '#C3B4E5',
    'ADAPTIVE CORE': '#F9D6B3',
    'ENERGY PATTERNS': '#E9C3E1',
    'Uncategorized': '#E0E0E0'
  }), []);

  // Memoize search results lookup for better performance
  const searchResultsMap = useMemo(() => {
    const map = new Map();
    searchResults.forEach(result => {
      map.set(result.id, result);
    });
    return map;
  }, [searchResults]);
  // Use filtered data if available, otherwise use full graph data
  const currentGraphData = filteredGraphData || graphData;

  const memoizedNodes = useMemo(() => {
    if (!currentGraphData.nodes || currentGraphData.nodes.length === 0) {
      return [];
    }
    
    return currentGraphData.nodes.map(node => {
      const isTheme = node.type === 'Theme';
      const isChatContext = chatContextNode && node.id === chatContextNode.id;
      const isSelected = selectedNode && node.id === selectedNode.id;
      
      // Optimized search result lookup using Map
      const searchResult = searchResultsMap.get(node.id);
      const isSearchResult = !!searchResult;
      
      const baseColor = typeColors[node.type] || typeColors['Uncategorized'];

      // Simulate the gradient: bright fill, original color border
      const fillColor = brightenHexColor(baseColor, 20); // 20% brighter for the center

      // Smart text handling for long labels - work within NVL's 2-line limit
      const originalText = node.label || '';
      const labelLength = originalText.length;
      
      // Simpler approach - let small fonts do the work
      const labelText = originalText; // Use original text, rely on tiny fonts
      
      const baseSize = isTheme ? 40 : 25;
      const minSize = baseSize;
      const maxSize = isTheme ? 120 : 100; // Even larger nodes for long text
      
      // More aggressive sizing for longer text
      const extraSize = Math.min(Math.max(0, labelLength - 10) * 2, maxSize - minSize);
      const dynamicSize = minSize + extraSize;
      
      // Aggressive font scaling based on text length
      const baseFontSize = isTheme ? 14 : 11;
      
      // Even more aggressive scaling - go smaller!
      let fontScale = 1.0;
      if (labelLength > 35) fontScale = 0.50;        // Very long text - super tiny font
      else if (labelLength > 30) fontScale = 0.55;   // Long text - very small font  
      else if (labelLength > 25) fontScale = 0.60;   // Medium-long text - small font
      else if (labelLength > 20) fontScale = 0.70;   // Medium text - somewhat small
      else if (labelLength > 15) fontScale = 0.80;   // Short-medium text - slightly small  
      else if (labelLength > 10) fontScale = 0.90;   // Short text - almost normal
      
      const smartFontSize = Math.max(Math.round(baseFontSize * fontScale), 6); // Allow down to 6px
      
      console.log(`📏 Text "${originalText}" (${labelLength} chars) -> font ${smartFontSize}px (scale: ${fontScale})`);
      
      // Multi-line caption support using proper NVL captions format
      const createCaptions = (text) => {
        // Debug long labels
        if (text.length > 15) {
          console.log('🏷️ Long label:', text, 'Length:', text.length);
        }
        
        if (text.length <= 30) {
          // Single caption with proper NVL format
          return [{ value: text, styles: [] }];
        }
        
        // Split long text into multiple lines at word boundaries
        const words = text.split(' ');
        const lines = [];
        let currentLine = '';
        
        for (const word of words) {
          if ((currentLine + ' ' + word).length <= 30) {
            currentLine = currentLine ? currentLine + ' ' + word : word;
          } else {
            if (currentLine) lines.push(currentLine);
            currentLine = word;
          }
        }
        if (currentLine) lines.push(currentLine);
        
        // Create proper NVL captions format with styles array
        const result = lines.slice(0, 3).map(line => ({ 
          value: line, 
          styles: [] // Empty styles array as required by NVL
        }));
        console.log('📝 Multi-line captions for', text, ':', result);
        return result;
      };
      
      // Back to single caption that was working
      let finalNode = {
        id: node.id,
        caption: labelText, // Use single caption that was working before
        size: dynamicSize,
        color: fillColor,
        font: {
          color: '#1E293B',
          strokeWidth: 0,
          size: smartFontSize,
          // Try word-break prevention properties
          wordBreak: 'keep-all',
          whiteSpace: 'nowrap',
          textOverflow: 'clip'
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
          fullData: node,
          searchScore: searchResult?.score // Add search score to properties
        }
      };

      // Chat context highlighting (takes precedence over search and selection)
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
      // Selected node highlighting (takes precedence over search)
      else if (isSelected) {
        finalNode = {
          ...finalNode,
          borderColor: '#F59E0B', // Amber/Orange border for selected
          borderWidth: 5,
          shadowEnabled: true,
          shadowColor: 'rgba(245, 158, 11, 0.5)',
          shadowBlur: 15,
          shadowOffsetX: 0,
          shadowOffsetY: 0,
          size: finalNode.size + 6, // Make it noticeably larger
        };
      }
      // Search result highlighting (if not already chat context or selected)
      else if (isSearchResult) {
        const searchScore = searchResult.score;
        // Different intensity based on score
        const intensity = Math.max(0.3, searchScore); // Minimum 30% intensity
        
        finalNode = {
          ...finalNode,
          borderColor: '#3B82F6', // Blue border for search results
          borderWidth: 5,
          shadowEnabled: true,
          shadowColor: `rgba(59, 130, 246, ${intensity * 0.6})`, // Dynamic shadow opacity
          shadowBlur: 15,
          shadowOffsetX: 0,
          shadowOffsetY: 0,
          // Slightly larger size for high-relevance results
          size: finalNode.size + (searchScore > 0.8 ? 8 : searchScore > 0.6 ? 5 : 3),
          // Add a subtle pulsing effect for very high relevance
          ...(searchScore > 0.8 && {
            animation: {
              enabled: true,
              type: 'pulse',
              duration: 2000,
              intensity: 0.2
            }
          })
        };
      }
      
      // Debug ALL nodes to see what's happening with captions
      if (labelLength > 5) {
        console.log('🔍 Node structure:', {
          id: finalNode.id,
          caption: finalNode.caption,
          captionSize: finalNode.captionSize,
          captionAlign: finalNode.captionAlign,
          size: finalNode.size,
          fontSize: finalNode.fontSize,
          font: finalNode.font
        });
      }
      
      return finalNode;
    });
  }, [currentGraphData.nodes, chatContextNode, selectedNode, searchResultsMap, typeColors]);

  // Memoize edge styling to avoid recreating style objects
  const edgeStyle = useMemo(() => ({
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
  }), []);

  const memoizedRels = useMemo(() => {
    if (!currentGraphData.edges || currentGraphData.edges.length === 0) {
      return [];
    }
    return currentGraphData.edges.map((edge, idx) => ({
      id: `rel-${idx}`,
      from: edge.from,
      to: edge.to,
      caption: edge.label,
      ...edgeStyle
    }));
  }, [currentGraphData.edges, edgeStyle]);

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
    
    // Debug: Log all available methods on nvlRef
    if (nvlRef.current) {
      console.log('=== NVL REF DEBUG ===');
      console.log('nvlRef.current:', nvlRef.current);
      
      // Check what renderer is actually being used
      const container = nvlRef.current.getContainer();
      if (container) {
        const canvas = container.querySelector('canvas');
        const svg = container.querySelector('svg');
        console.log('🎨 Canvas element found:', !!canvas);
        console.log('🖼️ SVG element found:', !!svg);
        if (canvas) {
          console.log('✅ Canvas renderer active');
        } else if (svg) {
          console.log('❌ SVG/WebGL renderer active - captions may not work');
        }
      }
      
      const allMethods = Object.getOwnPropertyNames(nvlRef.current).filter(name => typeof nvlRef.current[name] === 'function');
      console.log('ALL METHODS:', allMethods);
      
      // Check specifically for zoom-related methods
      const zoomMethods = allMethods.filter(name => 
        name.toLowerCase().includes('zoom') || 
        name.toLowerCase().includes('scale') ||
        name.toLowerCase().includes('fit') ||
        name.toLowerCase().includes('center') ||
        name.toLowerCase().includes('focus')
      );
      console.log('ZOOM/FOCUS METHODS:', zoomMethods);
      
      // Try to access nested objects that might contain zoom methods
      if (nvlRef.current.nvl) {
        console.log('nvlRef.current.nvl methods:', Object.getOwnPropertyNames(nvlRef.current.nvl).filter(name => typeof nvlRef.current.nvl[name] === 'function'));
      }
      if (nvlRef.current.network) {
        console.log('nvlRef.current.network methods:', Object.getOwnPropertyNames(nvlRef.current.network).filter(name => typeof nvlRef.current.network[name] === 'function'));
      }
      if (nvlRef.current.vis) {
        console.log('nvlRef.current.vis methods:', Object.getOwnPropertyNames(nvlRef.current.vis).filter(name => typeof nvlRef.current.vis[name] === 'function'));
      }
      console.log('=== END DEBUG ===');
    }
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
    console.log('Zoom in button clicked');
    if (!nvlRef.current) {
      console.log('nvlRef.current is null');
      return;
    }
    
    try {
      // Use the available setZoom method with getScale to get current zoom
      if (typeof nvlRef.current.setZoom === 'function' && typeof nvlRef.current.getScale === 'function') {
        const currentScale = nvlRef.current.getScale();
        const newScale = currentScale * 1.3; // 30% zoom in
        nvlRef.current.setZoom(newScale);
        console.log('Used setZoom method:', currentScale, '->', newScale);
      } else {
        console.warn('setZoom or getScale not available');
      }
    } catch (error) {
      console.error('Error zooming in:', error);
    }
  };

  const handleZoomOut = () => {
    console.log('Zoom out button clicked');
    if (!nvlRef.current) {
      console.log('nvlRef.current is null');
      return;
    }
    
    try {
      // Use the available setZoom method with getScale to get current zoom
      if (typeof nvlRef.current.setZoom === 'function' && typeof nvlRef.current.getScale === 'function') {
        const currentScale = nvlRef.current.getScale();
        const newScale = currentScale * 0.77; // ~30% zoom out  
        nvlRef.current.setZoom(newScale);
        console.log('Used setZoom method:', currentScale, '->', newScale);
      } else {
        console.warn('setZoom or getScale not available');
      }
    } catch (error) {
      console.error('Error zooming out:', error);
    }
  };

  // Function to focus on search results
  const zoomToSearchResults = useCallback((results = searchResults) => {
    console.log('zoomToSearchResults called with:', results);
    if (!nvlRef.current || !results || results.length === 0) {
      console.log('No nvlRef or no results to focus on');
      return;
    }
    
    const nodeIds = results.map(result => result.id);
    console.log('Trying to focus on node IDs:', nodeIds);
    const allMethods = Object.getOwnPropertyNames(nvlRef.current).filter(name => typeof nvlRef.current[name] === 'function');
    console.log('ALL SEARCH FOCUS METHODS:', allMethods);
    
    const focusMethods = allMethods.filter(name => 
      name.toLowerCase().includes('focus') || name.toLowerCase().includes('fit') || name.toLowerCase().includes('center')
    );
    console.log('FOCUS-RELATED METHODS:', focusMethods);
    
    try {
      // Use the available 'fit' method - this should work
      if (typeof nvlRef.current.fit === 'function') {
        console.log('Using fit method to focus on search results');
        nvlRef.current.fit();
      } else {
        console.warn('fit method not available');
      }
    } catch (error) {
      console.error('Error focusing on search results:', error);
    }
  }, [searchResults]);

  // Custom wheel event handler for improved zoom sensitivity
  useEffect(() => {
    const handleWheel = (event) => {
      if (!nvlRef.current) return;
      
      // Only handle wheel events when they're over the graph
      event.preventDefault();
      
      // Detect if this is a trackpad (small deltaY values) vs mouse wheel (larger deltaY values)
      const isTrackpad = Math.abs(event.deltaY) < 50;
      
      // Different sensitivity for trackpad vs mouse wheel
      const sensitivity = isTrackpad ? 5.0 : 2.0; // Much higher sensitivity for trackpad
      const currentZoom = nvlRef.current.getScale();
      
      // Adjust the multiplier based on input type
      const multiplier = isTrackpad ? -0.01 : -0.002;
      const delta = event.deltaY * multiplier * sensitivity;
      
      const newZoom = Math.max(0.1, Math.min(8, currentZoom + delta));
      
      // Only update if there's a meaningful change
      if (Math.abs(newZoom - currentZoom) > 0.001) {
        nvlRef.current.setZoom(newZoom);
        console.log(`${isTrackpad ? 'Trackpad' : 'Mouse wheel'} zoom:`, currentZoom, '->', newZoom);
      }
    };

    // Wait for nvlRef to be ready
    const checkAndAttach = setInterval(() => {
      const container = nvlRef.current?.getContainer();
      if (container) {
        container.addEventListener('wheel', handleWheel, { passive: false });
        clearInterval(checkAndAttach);
      }
    }, 100);
    
    return () => {
      clearInterval(checkAndAttach);
      const container = nvlRef.current?.getContainer();
      if (container) {
        container.removeEventListener('wheel', handleWheel);
      }
    };
  }, []);

  // Function to jump to a specific node
  const jumpToNode = useCallback((nodeId) => {
    console.log('🎯 jumpToNode called with:', nodeId);
    if (!nvlRef.current || !nodeId) {
      console.log('❌ No nvlRef or nodeId provided');
      return;
    }
    
    try {
      // First, check if the node exists in the current graph data
      const nodeExists = currentGraphData.nodes?.some(node => node.id === nodeId);
      if (!nodeExists) {
        console.warn('❌ Node not found in currentGraphData:', nodeId);
        return;
      }

      console.log('✅ Node exists in graph data');
      
      // Wait a bit for layout to stabilize before getting position
      setTimeout(() => {
        try {
          // Use the fit method to actually move the viewport to the node
          if (typeof nvlRef.current.fit === 'function') {
            console.log('🚀 Using fit() to jump to node');
            
            // Call fit with the specific node ID
            nvlRef.current.fit([nodeId], {
              maxZoom: 2.0, // Don't zoom in too much
              animate: true, // Smooth animation
              animationDuration: 500 // Half second animation
            });
            
            console.log('✅ Called fit() on node:', nodeId);
            
            // After fit animation completes, show indicator
            setTimeout(() => {
              const nodePosition = nvlRef.current.getPositionById(nodeId);
              if (!nodePosition || nodePosition.x === undefined || nodePosition.y === undefined) {
                console.error('❌ Cannot get node position after fit');
                return;
              }
              
              const container = nvlRef.current.getContainer();
              if (!container) {
                console.error('❌ Cannot get container');
                return;
              }
              
              // Get current pan position to calculate screen coordinates
              const currentPan = nvlRef.current.getPan();
              const currentZoom = nvlRef.current.getScale();
              const rect = container.getBoundingClientRect();
              
              console.log('📊 Current viewport state:', {
                pan: currentPan,
                zoom: currentZoom,
                nodePos: nodePosition,
                container: { width: rect.width, height: rect.height }
              });
              
              // Calculate screen position from graph coordinates
              // Screen position = (graph position - pan) * zoom + container center
              const screenX = (nodePosition.x - currentPan.x) * currentZoom + rect.width / 2;
              const screenY = (nodePosition.y - currentPan.y) * currentZoom + rect.height / 2;
              
              console.log('📍 Screen position:', screenX, screenY);
              
              // Remove any existing indicators
              const existingIndicators = container.querySelectorAll('.node-jump-indicator');
              existingIndicators.forEach(el => el.remove());
              
              // Create indicator at the calculated screen position
              const wrapper = document.createElement('div');
              wrapper.className = 'node-jump-indicator';
              wrapper.style.cssText = `
                position: absolute;
                left: ${screenX}px;
                top: ${screenY}px;
                transform: translate(-50%, -50%);
                pointer-events: none;
                z-index: 9999;
              `;
              
              // Create the pulsing circle
              const indicator = document.createElement('div');
              indicator.style.cssText = `
                width: 80px;
                height: 80px;
                border: 4px solid #F59E0B;
                border-radius: 50%;
                background: rgba(245, 158, 11, 0.2);
                animation: nodeJumpPulse 1.5s ease-in-out infinite;
              `;
              
              // Create the label
              const label = document.createElement('div');
              label.style.cssText = `
                position: absolute;
                top: -45px;
                left: 50%;
                transform: translateX(-50%);
                background: #F59E0B;
                color: white;
                padding: 6px 10px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                white-space: nowrap;
                box-shadow: 0 2px 8px rgba(0,0,0,0.3);
              `;
              label.textContent = nodeId;
              
              // Add keyframe animation if not exists
              if (!document.getElementById('node-jump-keyframes')) {
                const style = document.createElement('style');
                style.id = 'node-jump-keyframes';
                style.textContent = `
                  @keyframes nodeJumpPulse {
                    0% { transform: scale(1); opacity: 1; }
                    50% { transform: scale(1.3); opacity: 0.8; }
                    100% { transform: scale(1); opacity: 1; }
                  }
                `;
                document.head.appendChild(style);
              }
              
              // Ensure container has relative positioning
              const computedStyle = window.getComputedStyle(container);
              if (computedStyle.position === 'static') {
                container.style.position = 'relative';
              }
              
              // Assemble and add the indicator
              wrapper.appendChild(indicator);
              wrapper.appendChild(label);
              container.appendChild(wrapper);
              
              console.log('🎨 Created indicator at screen position');
              
              // Remove after 3 seconds
              setTimeout(() => {
                if (wrapper.parentNode) {
                  wrapper.remove();
                }
              }, 3000);
              
            }, 600); // Wait for fit animation to complete
            
          } else {
            console.error('❌ fit() method not available on nvlRef');
          }
          
        } catch (innerError) {
          console.error('💥 Error in jumpToNode:', innerError);
        }
      }, 200); // Initial delay for layout stability
      
    } catch (error) {
      console.error('💥 Error jumping to node:', error);
    }
  }, [currentGraphData]);
  // Expose methods to parent component via ref
  React.useImperativeHandle(ref, () => ({
    zoomToSearchResults,
    zoomIn: handleZoomIn,
    zoomOut: handleZoomOut,
    jumpToNode,
    fitToScreen: () => {
      if (!nvlRef.current) return;
      
      // Use the working method we discovered
      if (typeof nvlRef.current.fit === 'function') {
        nvlRef.current.fit();
      } else if (typeof nvlRef.current.fitToScreen === 'function') {
        nvlRef.current.fitToScreen();
      } else if (typeof nvlRef.current.zoomToFit === 'function') {
        nvlRef.current.zoomToFit();
      } else if (typeof nvlRef.current.resetZoom === 'function') {
        nvlRef.current.resetZoom();
      } else if (typeof nvlRef.current.setZoom === 'function') {
        nvlRef.current.setZoom(1);
      }
    }
  }), [zoomToSearchResults, jumpToNode]);

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

  if (isLoading) {
    return <LoadingSpinner message="Loading knowledge graph with 600+ nodes and 1,300+ relationships..." />;
  }

  if (error) {
    return (
      <div style={{ padding: '20px', color: 'red', backgroundColor: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '8px', margin: '20px' }}>
        <h3>Mental Model Loading Error</h3>
        <p>Failed to load mental model data: {error}</p>
        <button onClick={loadGraph} style={{ marginTop: '10px', padding: '8px 16px' }}>
          Retry
        </button>
      </div>
    );
  }

  console.log('Rendering GraphView with data:', memoizedNodes.length, 'nodes');
  console.log('🎨 Using canvas renderer - disableWebGL:', true);

  return (
    <div 
      style={{ position: 'relative', width: '100%', height: '100%' }}
      onKeyDown={handleKeyDown}
      tabIndex="0"
      role="application"
      aria-label="Knowledge graph visualization..."
    >
      {/* Graph Filter Status Indicator */}
      {graphFilterMode && (
        <div style={{
          position: 'absolute',
          top: '16px',
          left: '16px',
          zIndex: 1000,
          backgroundColor: '#3B82F6',
          color: 'white',
          padding: '8px 16px',
          borderRadius: '8px',
          fontSize: '14px',
          fontWeight: '500',
          boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
            <polyline points="3.27,6.96 12,12.01 20.73,6.96"></polyline>
            <line x1="12" y1="22.08" x2="12" y2="12"></line>
          </svg>
          <span>
            {graphFilterMode === 'node-only' ? 'Isolated Node:' : 'Node + Connections:'} {filteredNodeId}
          </span>
          {onClearGraphFilter && (
            <button
              onClick={onClearGraphFilter}
              style={{
                backgroundColor: 'rgba(255, 255, 255, 0.2)',
                border: 'none',
                borderRadius: '4px',
                color: 'white',
                padding: '4px 8px',
                fontSize: '12px',
                cursor: 'pointer',
                fontWeight: '500'
              }}
              title="Return to full graph (or press Escape)"
              onMouseEnter={(e) => {
                e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.3)';
              }}
              onMouseLeave={(e) => {
                e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.2)';
              }}
            >
              Show Full Graph
            </button>
          )}
        </div>
      )}

      {/* Loading Indicator for Subgraph */}
      {isLoadingSubgraph && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 1001,
          backgroundColor: 'rgba(255, 255, 255, 0.95)',
          padding: '20px',
          borderRadius: '12px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)'
        }}>
          <svg className="spinner" width="24" height="24" viewBox="0 0 24 24">
            <circle 
              className="spinner-circle" 
              cx="12" 
              cy="12" 
              r="10" 
              stroke="currentColor" 
              strokeWidth="2" 
              fill="none"
            />
          </svg>
          <span>Loading subgraph...</span>
        </div>
      )}
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
            border: '1px solid #AEAEAE',
            borderRadius: '12px',
            cursor: 'pointer',
            fontSize: '18px',
            fontWeight: '500',
            color: '#6c757d',
            transition: 'all 0.2s ease',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          title="Zoom In (or press +)"
          aria-label="Zoom in to the graph"
          onMouseEnter={(e) => {
            e.target.style.backgroundColor = '#F8FAFC';
            e.target.style.borderColor = '#999999';
          }}
          onMouseLeave={(e) => {
            e.target.style.backgroundColor = '#FFFFFF';
            e.target.style.borderColor = '#AEAEAE';
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
            border: '1px solid #AEAEAE',
            borderRadius: '12px',
            cursor: 'pointer',
            fontSize: '18px',
            fontWeight: '500',
            color: '#6c757d',
            transition: 'all 0.2s ease',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          title="Zoom Out (or press -)"
          aria-label="Zoom out from the graph"
          onMouseEnter={(e) => {
            e.target.style.backgroundColor = '#F8FAFC';
            e.target.style.borderColor = '#999999';
          }}
          onMouseLeave={(e) => {
            e.target.style.backgroundColor = '#FFFFFF';
            e.target.style.borderColor = '#AEAEAE';
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
            layout: 'forcedirected', // Correct NVL layout name
            initialZoom: 0.3, // Start zoomed out to see spacing effect
            allowDynamicMinZoom: true,
            minZoom: 0.1,
            maxZoom: 8,
            renderer: 'canvas', // Explicitly set canvas renderer
            // New options to control the NVL legend
            legend: {
              enabled: true,
              orientation: 'top-left', // Move legend to top-left
              isCollapsed: isLegendMinimized, // Control collapse state
              onToggle: () => setIsLegendMinimized(!isLegendMinimized), // Handle toggle
            },
          }}
          layoutOptions={{
            // Reduced spacing parameters by 15% from extreme values
            nodeSpacing: 425, // Reduced from 500 (15% decrease)
            edgeLength: 850, // Reduced from 1000 (15% decrease)
            repulsion: 8500, // Reduced from 10000 (15% decrease)
            attraction: 0.001, // Keep minimal attraction
            damping: 0.9, // Keep high damping for stability
            springLength: 850, // Reduced from 1000 (15% decrease)
            springConstant: 0.001, // Keep very loose springs
            centralGravity: 0.001, // Keep minimal central gravity
            gravitationalConstant: -850 // Reduced from -1000 (15% decrease)
          }}
          mouseEventCallbacks={mouseEventCallbacks}
          nvlCallbacks={nvlCallbacks}
        />
      )}
    </div>
  );
});

GraphView.displayName = 'GraphView';

export default GraphView; 