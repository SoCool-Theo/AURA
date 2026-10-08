import { useState } from 'react';
import type { PortfolioReportResponse } from '../../../types/report';
import { go } from '../../../app/routes';
import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';
import { formatPercent } from '../dashboardUi';
import {
  RETURN_VIEW_RANGES,
  visibleReturnPoints,
  type ReturnViewRange,
} from '../../analytics/returnSeriesRange';
import styles from '../DashboardIntegration.module.css';
import { PortfolioReturnChart } from './PortfolioReturnChart';

export function PortfolioPerformance({ portfolioId, report, loading, failed }: { portfolioId: string; report: PortfolioReportResponse | null; loading: boolean; failed: boolean }) {
  const [viewRange, setViewRange] = useState<ReturnViewRange>('1M');
  if (loading) return <Card className={`dashboard-performance-card ${styles.emptyPanel}`}><h3>Loading portfolio returns</h3><p role="status">Retrieving the latest immutable analysis report.</p></Card>;
  if (!report) return <Card className={`dashboard-performance-card ${styles.emptyPanel}`}><h3>Portfolio returns unavailable</h3><p>{failed ? 'The latest report could not be retrieved.' : 'Analyze this portfolio to create a saved return series.'}</p>{!failed && <button className="primary-btn" onClick={() => go(`analytics/${portfolioId}`)}>Analyze Portfolio</button>}</Card>;
  const points = report.analysis.portfolio_returns;
  const visiblePoints = visibleReturnPoints(points, viewRange);
  return <Card className="dashboard-performance-card"><div className="dashboard-card-header performance-header"><div className="dashboard-card-title"><span className="title-icon"><Icon name="trend" size={22} /></span><h2>Periodic Portfolio Returns</h2></div><div className={styles.rangeTabs} role="group" aria-label="Chart view range">{RETURN_VIEW_RANGES.map(range => <button type="button" key={range} className={range === viewRange ? styles.activeRange : ''} aria-pressed={range === viewRange} onClick={() => setViewRange(range)}>{range}</button>)}</div><div className="performance-return"><strong>{formatPercent(report.analysis.portfolio_metrics.annualized_return)}</strong><small>Annualized return</small></div></div>{points.length ? <><PortfolioReturnChart points={visiblePoints} /><p className={styles.rangeSummary}>Showing {visiblePoints.length} of {points.length} saved observations · anchored to {points[points.length - 1].date}</p></> : <div className={styles.emptyPanel}><h3>No return observations</h3><p>The saved report contains no portfolio return points.</p></div>}</Card>;
}
