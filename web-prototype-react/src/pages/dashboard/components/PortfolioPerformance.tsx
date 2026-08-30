import { useState } from 'react';
import type { PortfolioReportResponse } from '../../../types/report';
import { go } from '../../../app/routes';
import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';
import { formatPercent } from '../dashboardUi';
import styles from '../DashboardIntegration.module.css';
import { PortfolioReturnChart } from './PortfolioReturnChart';

type ViewRange = '1M' | '3M' | '6M' | '1Y' | 'ALL';

const VIEW_RANGES: ViewRange[] = ['1M', '3M', '6M', '1Y', 'ALL'];
const RANGE_MONTHS: Record<Exclude<ViewRange, 'ALL'>, number> = {
  '1M': 1,
  '3M': 3,
  '6M': 6,
  '1Y': 12,
};

function calendarCutoff(anchor: string, months: number): string | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(anchor);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const targetMonthIndex = year * 12 + month - 1 - months;
  const targetYear = Math.floor(targetMonthIndex / 12);
  const targetMonthIndexInYear = targetMonthIndex - targetYear * 12;
  const lastDay = new Date(Date.UTC(targetYear, targetMonthIndexInYear + 1, 0)).getUTCDate();
  return `${String(targetYear).padStart(4, '0')}-${String(targetMonthIndexInYear + 1).padStart(2, '0')}-${String(Math.min(day, lastDay)).padStart(2, '0')}`;
}

function visibleReturnPoints(
  points: PortfolioReportResponse['analysis']['portfolio_returns'],
  viewRange: ViewRange,
) {
  if (viewRange === 'ALL' || !points.length) return points;
  const anchor = points[points.length - 1].date;
  const cutoff = calendarCutoff(anchor, RANGE_MONTHS[viewRange]);
  if (!cutoff) return points;
  return points.filter(point => point.date >= cutoff && point.date <= anchor);
}

export function PortfolioPerformance({ portfolioId, report, loading, failed }: { portfolioId: string; report: PortfolioReportResponse | null; loading: boolean; failed: boolean }) {
  const [viewRange, setViewRange] = useState<ViewRange>('ALL');
  if (loading) return <Card className={`dashboard-performance-card ${styles.emptyPanel}`}><h3>Loading portfolio returns</h3><p role="status">Retrieving the latest immutable analysis report.</p></Card>;
  if (!report) return <Card className={`dashboard-performance-card ${styles.emptyPanel}`}><h3>Portfolio returns unavailable</h3><p>{failed ? 'The latest report could not be retrieved.' : 'Analyze this portfolio to create a saved return series.'}</p>{!failed && <button className="primary-btn" onClick={() => go(`analytics/${portfolioId}`)}>Analyze Portfolio</button>}</Card>;
  const points = report.analysis.portfolio_returns;
  const visiblePoints = visibleReturnPoints(points, viewRange);
  return <Card className="dashboard-performance-card"><div className="dashboard-card-header performance-header"><div className="dashboard-card-title"><span className="title-icon"><Icon name="trend" size={22} /></span><h2>Periodic Portfolio Returns</h2></div><div className={styles.rangeTabs} role="group" aria-label="Chart view range">{VIEW_RANGES.map(range => <button type="button" key={range} className={range === viewRange ? styles.activeRange : ''} aria-pressed={range === viewRange} onClick={() => setViewRange(range)}>{range}</button>)}</div><div className="performance-return"><strong>{formatPercent(report.analysis.portfolio_metrics.annualized_return)}</strong><small>Annualized return</small></div></div>{points.length ? <><PortfolioReturnChart points={visiblePoints} /><p className={styles.rangeSummary}>Showing {visiblePoints.length} of {points.length} backend-returned observations · anchored to {points[points.length - 1].date}</p></> : <div className={styles.emptyPanel}><h3>No return observations</h3><p>The saved report contains no portfolio return points.</p></div>}</Card>;
}
