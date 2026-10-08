import type { AssetReturnPoint, PortfolioReturnPoint } from '../../../types/analytics';
import { formatPortfolioReturnTick, portfolioReturnAxisTicks } from '../dashboardUi';
import styles from '../DashboardIntegration.module.css';

const PLOT_WIDTH = 668;
const PLOT_HEIGHT = 184;

function chartDomain(values: number[]): [number, number] {
  const observedMin = Math.min(...values);
  const observedMax = Math.max(...values);
  let baseMin = Math.min(0, observedMin);
  let baseMax = Math.max(0, observedMax);

  if (observedMin === observedMax) {
    const fallback = Math.max(Math.abs(observedMin) * 0.1, 0.001);
    baseMin = Math.min(0, observedMin - fallback);
    baseMax = Math.max(0, observedMax + fallback);
  }

  const padding = (baseMax - baseMin) * 0.08;
  const domainMin = baseMin < 0 ? baseMin - padding : 0;
  const domainMax = baseMax > 0 ? baseMax + padding : 0;
  return [domainMin, domainMax];
}

type ReturnPoint = PortfolioReturnPoint | AssetReturnPoint;

function returnValue(point: ReturnPoint): number {
  return 'portfolio_return' in point
    ? point.portfolio_return
    : point.asset_return;
}

export function PortfolioReturnChart({
  points,
  axisLabel = 'Portfolio return (%)',
  ariaLabel = 'Saved periodic portfolio returns by date',
}: {
  points: ReturnPoint[];
  axisLabel?: string;
  ariaLabel?: string;
}) {
  if (!points.length) return null;
  const values = points.map(returnValue);
  const [domainMin, domainMax] = chartDomain(values);
  const domainSpan = domainMax - domainMin;
  const ticks = portfolioReturnAxisTicks(domainMin, domainMax);
  const lastIndex = Math.max(points.length - 1, 1);
  const coordinates = points.map((point, index) => {
    const x = (index / lastIndex) * PLOT_WIDTH;
    const y = ((domainMax - returnValue(point)) / domainSpan) * PLOT_HEIGHT;
    return `${x},${y}`;
  }).join(' ');
  const dateLabels = points.length < 3
    ? points
    : [points[0], points[Math.floor((points.length - 1) / 2)], points[points.length - 1]];

  return <div className={styles.chartFrame}>
    <div className={styles.yAxisTitle}>{axisLabel}</div>
    <div className={styles.yTicks} aria-hidden="true">
      {ticks.map(tick => <span key={tick} style={{ top: `${((domainMax - tick) / domainSpan) * 100}%` }}>{formatPortfolioReturnTick(tick, domainSpan)}</span>)}
    </div>
    <div className={styles.plot}>
      <svg className={styles.chart} viewBox={`0 0 ${PLOT_WIDTH} ${PLOT_HEIGHT}`} preserveAspectRatio="none" role="img" aria-label={ariaLabel}>
        {ticks.map(tick => {
          const y = ((domainMax - tick) / domainSpan) * PLOT_HEIGHT;
          const isZero = Math.abs(tick) < domainSpan * 0.0001;
          return <line className={isZero ? styles.zeroLine : styles.gridLine} key={tick} x1="0" y1={y} x2={PLOT_WIDTH} y2={y} />;
        })}
        <polyline className={styles.seriesLine} points={coordinates} />
        {points.length === 1 && <circle className={styles.singlePoint} cx="0" cy={((domainMax - returnValue(points[0])) / domainSpan) * PLOT_HEIGHT} r="4" />}
      </svg>
    </div>
    <div className={styles.chartLabels}>{dateLabels.map(point => <span key={point.date}>{point.date}</span>)}</div>
    <div className={styles.xAxisTitle}>Date</div>
  </div>;
}
