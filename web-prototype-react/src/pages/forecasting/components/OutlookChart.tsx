import { forecastHorizons, forecastPercent, type OutlookMetric, type OutlookPoint } from '../forecastingUi';
import styles from '../Forecasting.module.css';

export function OutlookChart({ points, metric }: { points: OutlookPoint[]; metric: OutlookMetric }) {
  const ordered = [...points].sort((a, b) => a.horizonDays - b.horizonDays);
  const values = [0, ...ordered.flatMap(point => [point.estimate, ...(point.interval ? [point.interval.lower, point.interval.upper] : [])])];
  const min = Math.min(...values), max = Math.max(...values);
  const padding = Math.max((max - min) * 0.12, 0.001);
  const low = metric === 'volatility' ? 0 : min - padding, high = max + padding;
  const x = (day: number) => 70 + ((day - 7) / 23) * 510;
  const y = (value: number) => 210 - ((value - low) / (high - low)) * 170;
  const label = metric === 'return' ? 'Expected return (%)' : 'Forecast volatility (%) · non-annualized';
  return <figure className={styles.figure}>
    <div className={styles.chartScroll} tabIndex={0} role="region" aria-label="Forecast horizon chart">
      <svg viewBox="0 0 640 265" className={styles.chart} role="img" aria-label={label + ': ' + ordered.map(point => point.horizonDays + ' days ' + forecastPercent(point.estimate)).join(', ')}>
        <title>{label} by calendar-day horizon</title>
        {[0, 1, 2, 3, 4].map(tick => {
          const value = low + ((high - low) * tick / 4);
          return <g key={tick}><line x1="70" x2="600" y1={y(value)} y2={y(value)} className={styles.grid} /><text x="60" y={y(value) + 4} textAnchor="end">{forecastPercent(value)}</text></g>;
        })}
        <line x1="70" x2="600" y1={y(0)} y2={y(0)} className={styles.zero} />
        {forecastHorizons.map(day => <g key={day}><line x1={x(day)} x2={x(day)} y1="40" y2="210" className={styles.grid} /><text x={x(day)} y="232" textAnchor="middle">{day} days</text></g>)}
        {ordered.length > 1 && <polyline points={ordered.map(point => `${x(point.horizonDays)},${y(point.estimate)}`).join(' ')} className={styles.guide} />}
        {ordered.map(point => <g key={point.horizonDays}>
          {point.interval && <g className={styles.interval}><line x1={x(point.horizonDays)} x2={x(point.horizonDays)} y1={y(point.interval.lower)} y2={y(point.interval.upper)} /><line x1={x(point.horizonDays) - 7} x2={x(point.horizonDays) + 7} y1={y(point.interval.lower)} y2={y(point.interval.lower)} /><line x1={x(point.horizonDays) - 7} x2={x(point.horizonDays) + 7} y1={y(point.interval.upper)} y2={y(point.interval.upper)} /></g>}
          <circle cx={x(point.horizonDays)} cy={y(point.estimate)} r="6" className={styles.marker} />
          <text x={x(point.horizonDays) - 12} y={y(point.estimate) - 10} textAnchor="end" className={styles.pointLabel}>{forecastPercent(point.estimate, metric === 'return')}</text>
        </g>)}
        <text x="330" y="260" textAnchor="middle">Calendar days ahead from each forecast origin</text>
        <text x="70" y="20">{label}</text>
      </svg>
    </div>
    <figcaption>V1 provides one 30-day estimate. 7-, 14-, and 21-day estimates are not available yet. {ordered.some(point => point.interval) ? 'Range bars show nominal 80% asset prediction ranges.' : 'No calibrated portfolio prediction range is provided.'} Connecting lines, when multiple estimates are available, are visual guides only. This is not a daily price path.</figcaption>
  </figure>;
}
