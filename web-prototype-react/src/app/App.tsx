import { useEffect } from 'react';
import { ProtectedRoute } from '../auth/ProtectedRoute';
import { useAuth } from '../auth/useAuth';
import { useHashRoute } from '../hooks/useHashRoute';
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
import { AssetRiskDetailPage } from '../pages/reports/AssetRiskDetailPage';
import { SettingsPage } from '../pages/settings/SettingsPage';
import { SimulationsPage } from '../pages/simulations/SimulationsPage';
import { SimulationHistoryDetailPage } from '../pages/simulations/SimulationHistoryDetailPage';
import { WatchlistPage } from '../pages/watchlist/WatchlistPage';
import { AppLayout } from './AppLayout';
import { go } from './routes';

function App() {
  const route = useHashRoute();
  const { status } = useAuth();
  const isPublicAuthRoute = route.page === 'login' || route.page === 'signup';

  useEffect(() => {
    if (isPublicAuthRoute && status === 'authenticated') go('dashboard');
  }, [isPublicAuthRoute, status]);

  if (isPublicAuthRoute) {
    if (status === 'authenticated') return null;
    return route.page === 'login' ? <LoginPage /> : <RegisterPage />;
  }

  let content;
  switch (route.page) {
    case 'dashboard': content = <DashboardPage />; break;
    case 'portfolios': content = <PortfoliosPage />; break;
    case 'portfolio': content = <PortfolioDetailPage key={route.id} portfolioId={route.id} />; break;
    case 'analytics': content = <AnalyticsPage key={route.id} portfolioId={route.id} />; break;
    case 'simulations': content = route.id && route.reportId
      ? <SimulationHistoryDetailPage key={`${route.id}/${route.reportId}`} portfolioId={route.id} simulationId={route.reportId} />
      : <SimulationsPage key={route.id} portfolioId={route.id} />; break;
    case 'assistant': content = <AssistantPage
      key={[route.id, route.reportId, route.contextId].filter(Boolean).join('/')}
      portfolioId={route.id}
      reportId={route.reportId === 'report' ? route.contextId : route.contextId ? undefined : route.reportId}
      simulationId={route.reportId === 'simulation' ? route.contextId : undefined}
    />; break;
    case 'reports': content = route.id && route.reportId
      ? <ReportDetailPage key={`${route.id}/${route.reportId}`} portfolioId={route.id} reportId={route.reportId} focusAssetSection={route.contextId === 'assets'} />
      : <ReportsPage />; break;
    case 'asset': content = route.id && route.reportId && route.contextId
      ? <AssetRiskDetailPage key={`${route.id}/${route.reportId}/${route.contextId}`} portfolioId={route.id} reportId={route.reportId} assetSymbol={route.contextId} />
      : <NotFoundPage />; break;
    case 'watchlist': content = <WatchlistPage />; break;
    case 'learn': content = <LearnPage />; break;
    case 'create': content = <CreatePortfolioPage />; break;
    case 'settings': content = <SettingsPage />; break;
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
