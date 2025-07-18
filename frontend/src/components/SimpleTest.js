import React from 'react';

function SimpleTest() {
  console.log('SimpleTest component rendering...');
  
  return (
    <div style={{ padding: '20px', fontSize: '18px', color: 'red' }}>
      <h1>Simple Test Component</h1>
      <p>If you can see this, React is working!</p>
      <p>Current time: {new Date().toLocaleTimeString()}</p>
    </div>
  );
}

export default SimpleTest; 