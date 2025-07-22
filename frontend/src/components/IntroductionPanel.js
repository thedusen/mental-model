import React from 'react';
import './IntroductionPanel.css';

function IntroductionPanel({ isVisible, onClose, onAddChatMessage }) {
  if (!isVisible) return null;

  return (
    <div className="introduction-panel">
      <div className="panel-content">
        <div className="intro-header">
          <h2 className="intro-title">The Profit Architect</h2>
          <p className="intro-subtitle">Mental Model</p>
        </div>

        <div className="intro-sections">
          {/* Problem + Solution */}
          <div className="intro-section problem-solution-section">
            <h3>Is your business less profitable than it should be?</h3>
            <p className="section-description">
              This mental model reveals the unconscious patterns Dan uses to find what's really holding businesses back. 
              Explore the strategies and insights he's developed over decades of helping business owners.
            </p>
          </div>

          {/* Primary CTA */}
          <div className="intro-section cta-section">
            <div className="primary-cta">
              <h3>Get insights in 30 seconds</h3>
              <p className="cta-description">
                Ask about your biggest business challenge and get personalized insights.
              </p>
              <div className="question-suggestions">
                <button 
                  className="suggestion-button"
                  onClick={() => onAddChatMessage && onAddChatMessage("Why isn't my business more profitable? ")}
                >
                  <span className="suggestion-icon">💬</span>
                  <span>"Why isn't my business more profitable?"</span>
                </button>
                <button 
                  className="suggestion-button"
                  onClick={() => onAddChatMessage && onAddChatMessage("How do I stop being the bottleneck that's preventing my own business from growing? ")}
                >
                  <span className="suggestion-icon">🚧</span>
                  <span>"How do I stop being the bottleneck in my business?"</span>
                </button>
                <button 
                  className="suggestion-button"
                  onClick={() => onAddChatMessage && onAddChatMessage("Why do my employees always seem to misunderstand what I'm asking them to do? ")}
                >
                  <span className="suggestion-icon">🤔</span>
                  <span>"Why do my employees misunderstand my requests?"</span>
                </button>
              </div>
              <p className="cta-hint">Or explore the graph by clicking any topic that interests you.</p>
            </div>
          </div>

          {/* Expert Bio */}
          <div className="intro-section expert-section">
            <div className="expert-preview">
              <div className="expert-image-large">
                <img 
                  src="https://images.leadconnectorhq.com/image/f_webp/q_80/r_1200/u_https://assets.cdn.filesafe.space/fc6ju3qo7bievI1Q2LS3/media/65e698c9ff061d7ad6a2b0ad.png" 
                  alt="Dan Hackett" 
                  className="expert-photo-large"
                  onError={(e) => {
                    e.target.style.display = 'none';
                    e.target.nextSibling.style.display = 'block';
                  }}
                />
                <div className="expert-fallback-large" style={{display: 'none'}}>
                  <div className="expert-initials-large">DH</div>
                </div>
              </div>
              <p className="expert-preview-text">
                Dan Hackett, known as The Profit Architect, specializes in finding the real causes behind profit problems—especially for overwhelmed owners.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default IntroductionPanel;