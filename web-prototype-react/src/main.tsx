import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './app/App';
import { AuthProvider } from './auth/AuthContext';
import { PortfolioPrivacyProvider } from './privacy/PortfolioPrivacy';
import { LearnProgressProvider } from './learn/LearnProgress';
import './styles.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AuthProvider>
      <PortfolioPrivacyProvider><LearnProgressProvider><App /></LearnProgressProvider></PortfolioPrivacyProvider>
    </AuthProvider>
  </React.StrictMode>,
);
