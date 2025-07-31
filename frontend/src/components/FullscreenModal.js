import React, { useEffect, useCallback, useRef } from 'react';
import './FullscreenModal.css';

const FullscreenModal = ({ 
  mode = 'theater', // 'theater' | 'focus' | 'zen'
  isOpen = false,
  onClose,
  onModeChange,
  children 
}) => {
  const touchStartRef = useRef({ x: 0, y: 0, time: 0 });
  const modalRef = useRef(null);
  // Handle ESC key to close modal
  const handleKeyDown = useCallback((event) => {
    if (event.key === 'Escape' && isOpen) {
      onClose();
    }
  }, [isOpen, onClose]);

  // Handle backdrop click to close
  const handleBackdropClick = useCallback((event) => {
    if (event.target === event.currentTarget) {
      onClose();
    }
  }, [onClose]);

  // Touch gesture handling for mobile
  const handleTouchStart = useCallback((event) => {
    const touch = event.touches[0];
    touchStartRef.current = {
      x: touch.clientX,
      y: touch.clientY,
      time: Date.now()
    };
  }, []);

  const handleTouchEnd = useCallback((event) => {
    if (!touchStartRef.current.time) return;
    
    const touch = event.changedTouches[0];
    const deltaX = touch.clientX - touchStartRef.current.x;
    const deltaY = touch.clientY - touchStartRef.current.y;
    const deltaTime = Date.now() - touchStartRef.current.time;
    
    // Reset touch start
    touchStartRef.current = { x: 0, y: 0, time: 0 };
    
    // Check for valid swipe (minimum distance and maximum time)
    if (Math.abs(deltaX) < 50 && Math.abs(deltaY) < 50) return; // Too short
    if (deltaTime > 300) return; // Too slow
    
    const velocity = Math.sqrt(deltaX * deltaX + deltaY * deltaY) / deltaTime;
    if (velocity < 0.3) return; // Too slow
    
    // Determine swipe direction
    const angle = Math.atan2(Math.abs(deltaY), Math.abs(deltaX)) * 180 / Math.PI;
    
    // Vertical swipes (up/down)
    if (angle > 60) {
      if (deltaY < -50) {
        // Swipe up - cycle to next mode (theater <-> zen only)
        const modes = ['theater', 'zen'];
        const currentIndex = modes.indexOf(mode);
        const nextIndex = (currentIndex + 1) % modes.length;
        onModeChange(modes[nextIndex]);
      } else if (deltaY > 50) {
        // Swipe down - exit fullscreen
        onClose();
      }
    }
    // Horizontal swipes (left/right) - cycle modes
    else if (angle < 30) {
      const modes = ['theater', 'zen'];
      const currentIndex = modes.indexOf(mode);
      
      if (deltaX > 50) {
        // Swipe right - next mode
        const nextIndex = (currentIndex + 1) % modes.length;
        onModeChange(modes[nextIndex]);
      } else if (deltaX < -50) {
        // Swipe left - previous mode
        const prevIndex = (currentIndex - 1 + modes.length) % modes.length;
        onModeChange(modes[prevIndex]);
      }
    }
  }, [mode, onClose, onModeChange]);

  // Add/remove event listeners for keyboard shortcuts and touch events
  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      // Prevent body scroll when modal is open
      document.body.style.overflow = 'hidden';
      
      // Add touch event listeners for mobile gestures
      const modalElement = modalRef.current;
      if (modalElement) {
        modalElement.addEventListener('touchstart', handleTouchStart, { passive: true });
        modalElement.addEventListener('touchend', handleTouchEnd, { passive: true });
      }
      
      return () => {
        document.removeEventListener('keydown', handleKeyDown);
        document.body.style.overflow = 'unset';
        
        // Remove touch event listeners
        if (modalElement) {
          modalElement.removeEventListener('touchstart', handleTouchStart);
          modalElement.removeEventListener('touchend', handleTouchEnd);
        }
      };
    }
  }, [isOpen, handleKeyDown, handleTouchStart, handleTouchEnd]);

  // Focus management for accessibility
  useEffect(() => {
    if (isOpen) {
      // Focus the modal container for screen readers
      const modalElement = document.querySelector('.fullscreen-modal');
      if (modalElement) {
        modalElement.focus();
      }
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div 
      ref={modalRef}
      className={`fullscreen-modal fullscreen-modal-${mode}`}
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-label={`${mode} mode chat`}
      tabIndex={-1}
    >
      {/* Backdrop */}
      <div className={`fullscreen-backdrop fullscreen-backdrop-${mode}`} />
      
      {/* Modal Content */}
      <div 
        className={`fullscreen-content fullscreen-content-${mode}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Mode Controls */}
        <div className="fullscreen-controls">
          <div className="mode-selector">
            <button
              className={`mode-btn ${mode === 'theater' ? 'active' : ''}`}
              onClick={() => onModeChange('theater')}
              title="Theater Mode - Balanced immersion"
              aria-label="Switch to theater mode"
            >
              Theater
            </button>
            <button
              className={`mode-btn ${mode === 'zen' ? 'active' : ''}`}
              onClick={() => onModeChange('zen')}
              title="Zen Mode - Maximum immersion"
              aria-label="Switch to zen mode"
            >
              Zen
            </button>
          </div>
          
          <button 
            className="close-btn"
            onClick={onClose}
            title="Exit fullscreen (ESC)"
            aria-label="Exit fullscreen mode"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>

        {/* Chat Content */}
        <div className="fullscreen-chat-container">
          {children}
        </div>
      </div>
    </div>
  );
};

export default FullscreenModal;