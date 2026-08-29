import { useEffect } from 'react';
import { ProtectedRoute } from '../auth/ProtectedRoute';
import { useAuth } from '../auth/useAuth';
import { useHashRoute } from '../hooks/useHashRoute';
import { usePersistedState } from '../hooks/usePersistedState';
import { defaultPortfolios } from '../mocks/portfolios.mock';
import { reportsSeed } from '../mocks/reports.mock';
import { defaultSettings } from '../mocks/settings.mock';
import { watchlistSeed } from '../mocks/watchlist.mock';
import { AnalyticsPage } from '../pages/analytics/AnalyticsPage';
import { AssistantPage } from '../pages/assistant/AssistantPage';
import { LoginPage } from '../pages/auth/LoginPage';
import { RegisterPage } from '../pages/auth/RegisterPage';
import { DashboardPage } from '../pages/dashboard/DashboardPage';
import { LearnPage } from '../pages/learn/LearnPage';
import { NotFoundPage } from '../pages/not-found/NotFoundPage';
import { CreatePortfolioPage } from '../pages/portfolios/CreatePortfolioPage';
import { PortfolioDetailPage } from '../pages/portfolios/PortfolioDetailPage';
import { PortfoliosPage } from '../pages/portfolios/PortfoliosPage';
import { ReportsPage } from '../pages/reports/ReportsPage';
import { ReportDetailPage } from '../pages/reports/ReportDetailPage';
import { SettingsPage } from '../pages/settings/SettingsPage';
import { SimulationsPage } from '../pages/simulations/SimulationsPage';
import { WatchlistPage } from '../pages/watchlist/WatchlistPage';
import { AppLayout } from './AppLayout';
import { go } from './routes';

function App() {
  const route = useHashRoute();
  const { status } = useAuth();
  const [portfolios, setPortfolios] = usePersistedState('aura-portfolios', defaultPortfolios);
  const [reports, setReports] = usePersistedState('aura-reports', reportsSeed);
  const [watchlist, setWatchlist] = usePersistedState('aura-watchlist', watchlistSeed);
  const [settings, setSettings] = usePersistedState('aura-settings', defaultSettings);
  const isPublicAuthRoute = route.page === 'login' || route.page === 'signup';

  useEffect(() => {
    if (isPublicAuthRoute && status === 'authenticated') go('dashboard');
  }, [isPublicAuthRoute, status]);

  if (isPublicAuthRoute) {
    if (status === 'authenticated') return null;
    return route.page === 'login' ? <LoginPage /> : <RegisterPage />;
  }

  const activePortfolio = portfolios.find(p => p.id === (route.id || 'tech')) || portfolios[0];

  let content;
  switch (route.page) {
    case 'dashboard': content = <DashboardPage portfolios={portfolios} settings={settings} />; break;
    case 'portfolios': content = <PortfoliosPage portfolios={portfolios} setPortfolios={setPortfolios} />; break;
    case 'portfolio': content = <PortfolioDetailPage portfolio={activePortfolio} setPortfolios={setPortfolios} />; break;
    case 'analytics': content = <AnalyticsPage portfolio={activePortfolio} setReports={setReports} />; break;
    case 'simulations': content = <SimulationsPage portfolio={activePortfolio} portfolios={portfolios} setReports={setReports} />; break;
    case 'assistant': content = <AssistantPage portfolio={activePortfolio} />; break;
    case 'reports': content = route.id && route.reportId
      ? <ReportDetailPage portfolioId={route.id} reportId={route.reportId} />
      : <ReportsPage reports={reports} setReports={setReports} />; break;
    case 'watchlist': content = <WatchlistPage watchlist={watchlist} setWatchlist={setWatchlist} />; break;
    case 'learn': content = <LearnPage />; break;
    case 'create': content = <CreatePortfolioPage portfolios={portfolios} setPortfolios={setPortfolios} />; break;
    case 'settings': content = <SettingsPage settings={settings} setSettings={setSettings} />; break;
    case '404': content = <NotFoundPage />; break;
    default: content = <NotFoundPage />;
  }

  return (
    <ProtectedRoute>
      <AppLayout route={route}>{content}</AppLayout>
    </ProtectedRoute>
  );
}

export default App;
