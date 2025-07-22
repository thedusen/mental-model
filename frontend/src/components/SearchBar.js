import React, { useState, useRef, useEffect, useCallback } from 'react';
import './SearchBar.css';
import SearchResults from './SearchResults';

function SearchBar({ 
  onSearch, 
  onClear, 
  isLoading = false, 
  placeholder = "Search the mental model...",
  searchResults = [],
  searchQuery = '',
  searchExecutionTime = 0,
  isSearchResultsVisible = false,
  onResultClick,
  onFocusAll
}) {
  const [query, setQuery] = useState('');
  const [isActive, setIsActive] = useState(false);
  const [showValidation, setShowValidation] = useState(false);
  const [searchHistory, setSearchHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const inputRef = useRef(null);
  const debounceRef = useRef(null);

  // Debounced search function
  const debouncedSearch = useCallback((searchQuery) => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    
    debounceRef.current = setTimeout(() => {
      if (searchQuery.trim().length >= 2) {
        setShowValidation(false);
        if (onSearch) {
          onSearch(searchQuery.trim());
        }
      } else if (searchQuery.trim().length > 0) {
        setShowValidation(true);
      } else {
        setShowValidation(false);
        if (onClear) {
          onClear();
        }
      }
    }, 300);
  }, [onSearch, onClear]);

  // Load search history from localStorage on mount
  useEffect(() => {
    const savedHistory = localStorage.getItem('mental-model-search-history');
    if (savedHistory) {
      try {
        const parsed = JSON.parse(savedHistory);
        setSearchHistory(Array.isArray(parsed) ? parsed.slice(0, 10) : []);
      } catch (error) {
        console.warn('Failed to parse search history:', error);
        localStorage.removeItem('mental-model-search-history');
      }
    }
  }, []);

  // Save search history to localStorage
  const saveToHistory = useCallback((searchQuery) => {
    const trimmed = searchQuery.trim();
    if (trimmed.length < 2) return;

    setSearchHistory(prev => {
      const filtered = prev.filter(item => item !== trimmed);
      const newHistory = [trimmed, ...filtered].slice(0, 10);
      
      try {
        localStorage.setItem('mental-model-search-history', JSON.stringify(newHistory));
      } catch (error) {
        console.warn('Failed to save search history:', error);
      }
      
      return newHistory;
    });
  }, []);

  // Cleanup debounce on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

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
        setShowValidation(false);
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
    
    // Show/hide history based on query
    if (!value.trim() && searchHistory.length > 0) {
      setShowHistory(true);
    } else {
      setShowHistory(false);
    }
    
    // Trigger debounced search
    debouncedSearch(value);
  };

  const handleHistoryClick = (historyItem) => {
    setQuery(historyItem);
    setShowHistory(false);
    setShowValidation(false);
    if (onSearch) {
      onSearch(historyItem);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    // Form submit now only handles Enter key, actual search is debounced
    const trimmedQuery = query.trim();
    
    if (trimmedQuery.length >= 2 && onSearch) {
      // Cancel debounce and search immediately
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
      setShowValidation(false);
      setShowHistory(false);
      saveToHistory(trimmedQuery);
      onSearch(trimmedQuery);
    } else if (trimmedQuery.length > 0) {
      setShowValidation(true);
    }
  };

  const handleFocus = () => {
    setIsActive(true);
    // Show history if input is empty and there's history
    if (!query.trim() && searchHistory.length > 0) {
      setShowHistory(true);
    }
  };

  const handleBlur = () => {
    // Small delay to allow click events on search results and history
    setTimeout(() => {
      setIsActive(false);
      setShowHistory(false);
    }, 150);
  };

  const handleClearClick = () => {
    setQuery('');
    setIsActive(false);
    setShowValidation(false);
    // Cancel any pending debounced search
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    if (inputRef.current) {
      inputRef.current.focus();
    }
    if (onClear) {
      onClear();
    }
  };

  return (
    <div className={`search-bar ${isActive ? 'active' : ''} ${isLoading ? 'loading' : ''}`}>
      <form onSubmit={handleSubmit} className="search-form" role="search" aria-label="Search mental model">
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
            className={`search-input ${showValidation ? 'validation-error' : ''}`}
            autoComplete="off"
            aria-label="Search mental model"
            aria-describedby={`search-hint ${showValidation ? 'search-validation' : ''}`.trim()}
            aria-invalid={showValidation}
            aria-expanded={isSearchResultsVisible}
            aria-haspopup="listbox"
            aria-owns="search-results-listbox"
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
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          )}

          {/* Search Button */}
          {!isLoading && query.trim().length > 0 && (
            <button
              type="submit"
              className={`search-button ${query.trim().length < 2 ? 'disabled' : ''}`}
              disabled={query.trim().length < 2}
              aria-label="Search"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8"></circle>
                <path d="m21 21-4.35-4.35"></path>
              </svg>
              <span>Search</span>
            </button>
          )}

          {/* Keyboard Hint */}
          {!isActive && !query && (
            <div className="search-hint" id="search-hint">
              <kbd>⌘</kbd><kbd>K</kbd>
            </div>
          )}
        </div>
        
        {/* Validation Message */}
        {showValidation && (
          <div className="search-validation" id="search-validation" role="alert">
            Search requires at least 2 characters
          </div>
        )}
        
        {/* Search History Dropdown */}
        {showHistory && searchHistory.length > 0 && (
          <div className="search-history" role="listbox" aria-label="Recent searches">
            <div className="search-history-header">Recent Searches</div>
            {searchHistory.map((item, index) => (
              <button
                key={index}
                type="button"
                className="search-history-item"
                onClick={() => handleHistoryClick(item)}
                role="option"
                aria-label={`Search for "${item}"`}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <span>{item}</span>
              </button>
            ))}
          </div>
        )}
      </form>
      
      {/* Search Results Dropdown */}
      <SearchResults
        results={searchResults}
        query={searchQuery}
        isLoading={isLoading}
        executionTime={searchExecutionTime}
        isVisible={isSearchResultsVisible}
        onResultClick={onResultClick}
        onFocusAll={onFocusAll}
        onClear={onClear}
      />
    </div>
  );
}

export default SearchBar;