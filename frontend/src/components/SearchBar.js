import React, { useState, useRef, useEffect } from 'react';
import './SearchBar.css';

function SearchBar({ onSearch, onClear, isLoading = false, placeholder = "Search the knowledge graph..." }) {
  const [query, setQuery] = useState('');
  const [isActive, setIsActive] = useState(false);
  const inputRef = useRef(null);

  // Keyboard shortcut handler (Cmd/Ctrl + K)
  useEffect(() => {
    const handleKeyDown = (event) => {
      // Cmd+K (Mac) or Ctrl+K (Windows/Linux) to focus search
      if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
        event.preventDefault();
        setIsActive(true);
        if (inputRef.current) {
          inputRef.current.focus();
        }
      }
      
      // Escape to blur and clear
      if (event.key === 'Escape' && isActive) {
        event.preventDefault();
        setIsActive(false);
        setQuery('');
        if (inputRef.current) {
          inputRef.current.blur();
        }
        if (onClear) {
          onClear();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isActive, onClear]);

  const handleInputChange = (e) => {
    const value = e.target.value;
    setQuery(value);
    
    // Clear search results when query is empty
    if (!value.trim() && onClear) {
      onClear();
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmedQuery = query.trim();
    
    if (trimmedQuery.length >= 2 && onSearch) {
      onSearch(trimmedQuery);
    }
  };

  const handleFocus = () => {
    setIsActive(true);
  };

  const handleBlur = () => {
    // Small delay to allow click events on search results
    setTimeout(() => setIsActive(false), 150);
  };

  const handleClearClick = () => {
    setQuery('');
    setIsActive(false);
    if (inputRef.current) {
      inputRef.current.focus();
    }
    if (onClear) {
      onClear();
    }
  };

  return (
    <div className={`search-bar ${isActive ? 'active' : ''} ${isLoading ? 'loading' : ''}`}>
      <form onSubmit={handleSubmit} className="search-form">
        <div className="search-input-container">
          {/* Search Icon */}
          <svg 
            className="search-icon" 
            width="16" 
            height="16" 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="currentColor" 
            strokeWidth="2" 
            strokeLinecap="round" 
            strokeLinejoin="round"
          >
            <circle cx="11" cy="11" r="8"></circle>
            <path d="m21 21-4.35-4.35"></path>
          </svg>

          {/* Input Field */}
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={handleInputChange}
            onFocus={handleFocus}
            onBlur={handleBlur}
            placeholder={placeholder}
            className="search-input"
            autoComplete="off"
            aria-label="Search knowledge graph"
            aria-describedby="search-hint"
          />

          {/* Loading Spinner */}
          {isLoading && (
            <div className="search-loading">
              <svg className="spinner" width="16" height="16" viewBox="0 0 24 24">
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
          )}

          {/* Clear Button */}
          {query && !isLoading && (
            <button
              type="button"
              onClick={handleClearClick}
              className="search-clear"
              aria-label="Clear search"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          )}

          {/* Keyboard Hint */}
          {!isActive && !query && (
            <div className="search-hint" id="search-hint">
              <kbd>⌘</kbd><kbd>K</kbd>
            </div>
          )}
        </div>
      </form>
    </div>
  );
}

export default SearchBar;