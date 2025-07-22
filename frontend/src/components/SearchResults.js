import React, { useState, useEffect, useRef } from 'react';
import './SearchResults.css';

function SearchResults({ 
  results = [], 
  query = '', 
  isLoading = false, 
  executionTime = 0,
  onResultClick,
  onFocusAll,
  onClear,
  isVisible = false 
}) {
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const resultsRef = useRef(null);

  // Reset selection when results change
  useEffect(() => {
    setSelectedIndex(-1);
  }, [results]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (!isVisible || results.length === 0) return;

      switch (event.key) {
        case 'ArrowDown':
          event.preventDefault();
          setSelectedIndex(prev => Math.min(prev + 1, results.length - 1));
          break;
        case 'ArrowUp':
          event.preventDefault();
          setSelectedIndex(prev => Math.max(prev - 1, -1));
          break;
        case 'Enter':
          event.preventDefault();
          if (selectedIndex >= 0 && selectedIndex < results.length) {
            handleResultClick(results[selectedIndex]);
          }
          break;
        case 'Escape':
          event.preventDefault();
          if (onClear) onClear();
          break;
      }
    };

    if (isVisible) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isVisible, results, selectedIndex, onClear]);

  // Scroll selected item into view
  useEffect(() => {
    if (selectedIndex >= 0 && resultsRef.current) {
      const selectedElement = resultsRef.current.children[selectedIndex];
      if (selectedElement) {
        selectedElement.scrollIntoView({
          block: 'nearest',
          behavior: 'smooth'
        });
      }
    }
  }, [selectedIndex]);

  const handleResultClick = (result) => {
    if (onResultClick) {
      onResultClick(result);
    }
  };

  const handleFocusAllClick = () => {
    if (onFocusAll && results.length > 0) {
      onFocusAll(results);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 0.8) return '#059669'; // Darker green for high relevance (WCAG AA compliant)
    if (score >= 0.6) return '#d97706'; // Darker orange for medium relevance (WCAG AA compliant)  
    return '#374151'; // Darker gray for lower relevance (WCAG AA compliant)
  };

  const getScoreLabel = (score) => {
    if (score >= 0.8) return 'Highly relevant';
    if (score >= 0.6) return 'Relevant';
    return 'Somewhat relevant';
  };

  if (!isVisible) return null;

  return (
    <div className="search-results-overlay">
      {/* ARIA live region for search result announcements */}
      <div 
        aria-live="polite" 
        aria-atomic="true" 
        className="sr-only"
        id="search-results-live-region"
      >
        {!isLoading && results.length > 0 && (
          `${results.length} search result${results.length !== 1 ? 's' : ''} found for ${query}`
        )}
        {!isLoading && results.length === 0 && query && (
          `No search results found for ${query}`
        )}
      </div>
      
      <div 
        className="search-results-panel"
        role="listbox"
        id="search-results-listbox"
        aria-label={`Search results for "${query}"`}
      >
        {/* Header */}
        <div className="search-results-header">
          <div className="search-results-info">
            {isLoading ? (
              <span className="search-status loading">Searching...</span>
            ) : results.length > 0 ? (
              <span className="search-status">
                {results.length} result{results.length !== 1 ? 's' : ''} for "{query}"
                {executionTime > 0 && (
                  <span className="execution-time"> • {executionTime}ms</span>
                )}
              </span>
            ) : query ? (
              <span className="search-status no-results">No results found for "{query}"</span>
            ) : null}
          </div>
          
          <div className="search-results-actions">
            {results.length > 1 && (
              <button
                onClick={handleFocusAllClick}
                className="action-button focus-all"
                title="Zoom to show all search results in the graph visualization"
                aria-label="Zoom graph to show all search results"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="3"></circle>
                  <circle cx="12" cy="12" r="11"></circle>
                  <path d="m12 1 0 6"></path>
                  <path d="m12 17 0 6"></path>
                  <path d="m4.22 4.22 4.24 4.24"></path>
                  <path d="m15.54 15.54 4.24 4.24"></path>
                  <path d="m1 12 6 0"></path>
                  <path d="m17 12 6 0"></path>
                  <path d="m4.22 19.78 4.24-4.24"></path>
                  <path d="m15.54 8.46 4.24-4.24"></path>
                </svg>
                Focus All
              </button>
            )}
            
            <button
              onClick={onClear}
              className="action-button close"
              title="Clear search results"
              aria-label="Clear search results"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="search-loading-state">
            <div className="search-loading-spinner">
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
            </div>
            <p>Searching knowledge graph...</p>
          </div>
        )}

        {/* Results List */}
        {!isLoading && results.length > 0 && (
          <div className="search-results-list" ref={resultsRef}>
            {results.map((result, index) => (
              <div
                key={result.id}
                className={`search-result-item ${selectedIndex === index ? 'selected' : ''}`}
                onClick={() => handleResultClick(result)}
                onMouseEnter={() => setSelectedIndex(index)}
                role="option"
                tabIndex={-1}
                aria-selected={selectedIndex === index}
                aria-label={`${result.id}, ${result.type}, relevance ${(result.score * 100).toFixed(0)}%`}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleResultClick(result);
                  }
                }}
              >
                <div className="result-header">
                  <h3 className="result-title">{result.id}</h3>
                  <div className="result-meta">
                    <span 
                      className="result-score"
                      style={{ color: getScoreColor(result.score) }}
                      title={getScoreLabel(result.score)}
                    >
                      {(result.score * 100).toFixed(0)}%
                    </span>
                    <span className="result-type">{result.type}</span>
                  </div>
                </div>
                
                {result.description && (
                  <p className="result-description">
                    {result.description.length > 150 
                      ? `${result.description.substring(0, 150)}...`
                      : result.description
                    }
                  </p>
                )}
                
                {result.theme && (
                  <div className="result-theme">
                    <span className="theme-label">Theme:</span>
                    <span className="theme-name">{result.theme}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Empty State */}
        {!isLoading && results.length === 0 && query && (
          <div className="search-empty-state">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="11" cy="11" r="8"></circle>
              <path d="m21 21-4.35-4.35"></path>
            </svg>
            <h3>No results found</h3>
            <p>Try adjusting your search terms or use different keywords.</p>
            <div className="search-tips">
              <h4>Search tips:</h4>
              <ul>
                <li>Use specific concepts like "decision making" or "leadership"</li>
                <li>Try synonyms or related terms</li>
                <li>Search for patterns, principles, or examples</li>
              </ul>
            </div>
          </div>
        )}

        {/* Keyboard Hints */}
        {results.length > 0 && (
          <div className="search-keyboard-hints">
            <span>
              <kbd>↑</kbd><kbd>↓</kbd> Navigate
            </span>
            <span>
              <kbd>Enter</kbd> Select
            </span>
            <span>
              <kbd>Esc</kbd> Close
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

export default SearchResults;