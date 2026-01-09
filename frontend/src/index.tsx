// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
// CSS import after App ensures Tailwind utilities override component styles
import './index.css';
import { ThemeProvider } from './contexts/ThemeContext';

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </React.StrictMode>
);
