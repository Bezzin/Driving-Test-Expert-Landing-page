import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

console.log('index.tsx loaded');

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error("Could not find root element to mount to");
}

console.log('Root element found, creating React root...');

const root = ReactDOM.createRoot(rootElement);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

console.log('React app rendered');