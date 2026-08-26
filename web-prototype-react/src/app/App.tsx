// @ts-nocheck
import React, { useEffect, useState } from 'react';
import { Card } from '../components/ui/Card';
import { Icon } from '../components/ui/Icon';
import { usePersistedState } from '../hooks/usePersistedState';
import { defaultPortfolios } from '../mocks/portfolios.mock';
import { reportsSeed } from '../mocks/reports.mock';
import { defaultSettings } from '../mocks/settings.mock';
import { watchlistSeed } from '../mocks/watchlist.mock';
import { AnalyticsPage } from '../pages/analytics/AnalyticsPage';
import { AssistantPage } from '../pages/assistant/AssistantPage';
import { DashboardPage } from '../pages/dashboard/DashboardPage';
import { LearnPage } from '../pages/learn/LearnPage';
import { CreatePortfolioPage } from '../pages/portfolios/CreatePortfolioPage';
import { PortfolioDetailPage } from '../pages/portfolios/PortfolioDetailPage';
import { PortfoliosPage } from '../pages/portfolios/PortfoliosPage';
import { ReportsPage } from '../pages/reports/ReportsPage';
import { SettingsPage } from '../pages/settings/SettingsPage';
import { SimulationsPage } from '../pages/simulations/SimulationsPage';
import { WatchlistPage } from '../pages/watchlist/WatchlistPage';
import { AppLayout } from './AppLayout';
import { go, routeFromHash } from './routes';

function App() {
  const [route, setRoute] = useState(routeFromHash());
  const [portfolios, setPortfolios] = usePersistedState('aura-portfolios', defaultPortfolios);
  const [reports, setReports] = usePersistedState('aura-reports', reportsSeed);
  const [watchlist, setWatchlist] = usePersistedState('aura-watchlist', watchlistSeed);
  const [settings, setSettings] = usePersistedState('aura-settings', defaultSettings);

  useEffect(() => {
    const handler = () => setRoute(routeFromHash());
    window.addEventListener('hashchange', handler);
    if (!window.location.hash) go('dashboard');
    return () => window.removeEventListener('hashchange', handler);
  }, []);

  const activePortfolio = portfolios.find(p => p.id === (route.id || 'tech')) || portfolios[0];
  const shared = { portfolios, setPortfolios, reports, setReports, watchlist, setWatchlist, settings, setSettings };

  let content;
  switch (route.page) {
    case 'dashboard': content = <DashboardPage portfolios={portfolios} settings={settings} />; break;
    case 'portfolios': content = <PortfoliosPage portfolios={portfolios} setPortfolios={setPortfolios} />; break;
    case 'portfolio': content = <PortfolioDetailPage portfolio={activePortfolio} setPortfolios={setPortfolios} />; break;
    case 'analytics': content = <AnalyticsPage portfolio={activePortfolio} setReports={setReports} />; break;
    case 'simulations': content = <SimulationsPage portfolio={activePortfolio} setReports={setReports} />; break;
    case 'assistant': content = <AssistantPage portfolio={activePortfolio} />; break;
    case 'reports': content = <ReportsPage reports={reports} setReports={setReports} />; break;
    case 'watchlist': content = <WatchlistPage watchlist={watchlist} setWatchlist={setWatchlist} />; break;
    case 'learn': content = <LearnPage />; break;
    case 'create': content = <CreatePortfolioPage portfolios={portfolios} setPortfolios={setPortfolios} />; break;
    case 'settings': content = <SettingsPage settings={settings} setSettings={setSettings} />; break;
    default: content = <DashboardPage portfolios={portfolios} settings={settings} />;
  }

  return <AppLayout route={route} settings={settings}>{content}</AppLayout>;
}

function CardTitle({ title, right }) {
  return <div className="card-title"><h3>{title}</h3>{right}</div>;
}

function FeatureCard({ icon, title, text, button, onClick, tone = 'purple' }) {
  return <Card className={`feature-card ${tone}`}><div className="feature-icon">{icon}</div><div><h3>{title}</h3><p>{text}</p><button onClick={onClick}>{button}</button></div></Card>;
}

export default App;
