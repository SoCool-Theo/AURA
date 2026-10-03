import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './app/App';
import { AuthProvider } from './auth/AuthContext';
import { PortfolioPrivacyProvider } from './privacy/PortfolioPrivacy';
import './styles.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AuthProvider>
      <PortfolioPrivacyProvider><App /></PortfolioPrivacyProvider>
    </AuthProvider>
  </React.StrictMode>,
);
