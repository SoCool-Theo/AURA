import type { PortfolioReturnPoint } from '../../../types/analytics';
import styles from '../DashboardIntegration.module.css';

const PLOT_WIDTH = 668;
const PLOT_HEIGHT = 184;
const TICK_COUNT = 5;

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

function axisTicks(domainMin: number, domainMax: number): number[] {
  const interval = (domainMax - domainMin) / (TICK_COUNT - 1);
  const ticks = Array.from(
    { length: TICK_COUNT },
    (_, index) => domainMax - interval * index,
  );
  if (!ticks.some(tick => Math.abs(tick) < interval * 0.001)) ticks.push(0);
  return ticks.sort((left, right) => right - left);
}

function formatPercentTick(value: number, domainSpan: number): string {
  const percentSpan = domainSpan * 100;
  const fractionDigits = percentSpan < 1 ? 2 : percentSpan < 10 ? 1 : 0;
  return `${(value * 100).toFixed(fractionDigits)}%`;
}

export function PortfolioReturnChart({ points }: { points: PortfolioReturnPoint[] }) {
  if (!points.length) return null;
  const values = points.map(point => point.portfolio_return);
  const [domainMin, domainMax] = chartDomain(values);
  const domainSpan = domainMax - domainMin;
  const ticks = axisTicks(domainMin, domainMax);
  const lastIndex = Math.max(points.length - 1, 1);
  const coordinates = points.map((point, index) => {
    const x = (index / lastIndex) * PLOT_WIDTH;
    const y = ((domainMax - point.portfolio_return) / domainSpan) * PLOT_HEIGHT;
    return `${x},${y}`;
  }).join(' ');
  const dateLabels = points.length < 3
    ? points
    : [points[0], points[Math.floor((points.length - 1) / 2)], points[points.length - 1]];

  return <div className={styles.chartFrame}>
    <div className={styles.yAxisTitle}>Portfolio return (%)</div>
    <div className={styles.yTicks} aria-hidden="true">
      {ticks.map(tick => <span key={tick} style={{ top: `${((domainMax - tick) / domainSpan) * 100}%` }}>{formatPercentTick(tick, domainSpan)}</span>)}
    </div>
    <div className={styles.plot}>
      <svg className={styles.chart} viewBox={`0 0 ${PLOT_WIDTH} ${PLOT_HEIGHT}`} preserveAspectRatio="none" role="img" aria-label="Saved periodic portfolio returns by date">
        {ticks.map(tick => {
          const y = ((domainMax - tick) / domainSpan) * PLOT_HEIGHT;
          const isZero = Math.abs(tick) < domainSpan * 0.0001;
          return <line className={isZero ? styles.zeroLine : styles.gridLine} key={tick} x1="0" y1={y} x2={PLOT_WIDTH} y2={y} />;
        })}
        <polyline className={styles.seriesLine} points={coordinates} />
        {points.length === 1 && <circle className={styles.singlePoint} cx="0" cy={((domainMax - points[0].portfolio_return) / domainSpan) * PLOT_HEIGHT} r="4" />}
      </svg>
    </div>
    <div className={styles.chartLabels}>{dateLabels.map(point => <span key={point.date}>{point.date}</span>)}</div>
    <div className={styles.xAxisTitle}>Date</div>
  </div>;
}
