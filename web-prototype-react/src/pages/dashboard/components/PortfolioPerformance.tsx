import type { PortfolioReportResponse } from '../../../types/report';
import { go } from '../../../app/routes';
import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';
import { formatPercent } from '../dashboardUi';
import styles from '../DashboardIntegration.module.css';
import { PortfolioReturnChart } from './PortfolioReturnChart';

export function PortfolioPerformance({ portfolioId, report, loading, failed }: { portfolioId: string; report: PortfolioReportResponse | null; loading: boolean; failed: boolean }) {
  if (loading) return <Card className={`dashboard-performance-card ${styles.emptyPanel}`}><h3>Loading portfolio returns</h3><p role="status">Retrieving the latest immutable analysis report.</p></Card>;
  if (!report) return <Card className={`dashboard-performance-card ${styles.emptyPanel}`}><h3>Portfolio returns unavailable</h3><p>{failed ? 'The latest report could not be retrieved.' : 'Analyze this portfolio to create a saved return series.'}</p>{!failed && <button className="primary-btn" onClick={() => go(`analytics/${portfolioId}`)}>Analyze Portfolio</button>}</Card>;
  const points = report.analysis.portfolio_returns;
  return <Card className="dashboard-performance-card"><div className="dashboard-card-header performance-header"><div className="dashboard-card-title"><span className="title-icon"><Icon name="trend" size={22} /></span><h2>Periodic Portfolio Returns</h2></div><div className="performance-return"><strong>{formatPercent(report.analysis.portfolio_metrics.annualized_return)}</strong><small>Annualized return</small></div></div>{points.length ? <PortfolioReturnChart points={points} /> : <div className={styles.emptyPanel}><h3>No return observations</h3><p>The saved report contains no portfolio return points.</p></div>}</Card>;
}
