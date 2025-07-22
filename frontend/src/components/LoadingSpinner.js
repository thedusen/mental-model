import React from 'react';

const LoadingSpinner = ({ message = "Loading mental model..." }) => {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100%',
      width: '100%',
      backgroundColor: '#F8FAFC',
      color: '#475569'
    }}>
      <div style={{
        width: '60px',
        height: '60px',
        border: '4px solid #E2E8F0',
        borderTop: '4px solid #3B82F6',
        borderRadius: '50%',
        animation: 'spin 1s linear infinite',
        marginBottom: '20px'
      }} />
      <p style={{
        fontSize: '16px',
        fontWeight: '500',
        margin: '0',
        textAlign: 'center'
      }}>
        {message}
      </p>
    </div>
  );
};

export default LoadingSpinner;