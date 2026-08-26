import { useHashRoute } from '../hooks/useHashRoute';
import { usePersistedState } from '../hooks/usePersistedState';
import { defaultPortfolios } from '../mocks/portfolios.mock';
import { reportsSeed } from '../mocks/reports.mock';
import { defaultSettings } from '../mocks/settings.mock';
import { watchlistSeed } from '../mocks/watchlist.mock';
import { AnalyticsPage } from '../pages/analytics/AnalyticsPage';
import { AssistantPage } from '../pages/assistant/AssistantPage';
import { LoginPage } from '../pages/auth/LoginPage';
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

function App() {
  const route = useHashRoute();
  const [portfolios, setPortfolios] = usePersistedState('aura-portfolios', defaultPortfolios);
  const [reports, setReports] = usePersistedState('aura-reports', reportsSeed);
  const [watchlist, setWatchlist] = usePersistedState('aura-watchlist', watchlistSeed);
  const [settings, setSettings] = usePersistedState('aura-settings', defaultSettings);

  if (route.page === 'login') return <LoginPage />;

  const activePortfolio = portfolios.find(p => p.id === (route.id || 'tech')) || portfolios[0];

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

export default App;
