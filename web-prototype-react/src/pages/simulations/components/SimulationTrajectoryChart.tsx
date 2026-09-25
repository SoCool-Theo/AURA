import { useState } from 'react';
import type { HistoricalScenarioTrajectoryPoint } from '../../../types/simulation';
import styles from '../SimulationIntegration.module.css';

interface Series { label: string; color: string; points: HistoricalScenarioTrajectoryPoint[] }

export function SimulationTrajectoryChart({ series }: { series: Series[] }) {
  const [selectedSeries, setSelectedSeries] = useState('all');
  const visibleSeries = selectedSeries === 'all'
    ? series
    : series.filter(item => item.label === selectedSeries);
  const values = visibleSeries.flatMap(item => item.points.map(point => point.normalized_value));
  if (!values.length) return <p>No trajectory observations were returned.</p>;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const left = 62;
  const right = 582;
  const top = 28;
  const middle = 130;
  const bottom = 232;
  const selectedPoints = selectedSeries === 'all' ? null : visibleSeries[0]?.points;
  const polylines = visibleSeries.map(item => {
    const lastIndex = Math.max(item.points.length - 1, 1);
    const points = item.points.map((point, index) => {
      const x = left + (index / lastIndex) * (right - left);
      const y = bottom - ((point.normalized_value - min) / range) * (bottom - top);
      return `${x},${y}`;
    }).join(' ');
    return <polyline key={item.label} points={points} stroke={item.color} />;
  });

  return <>
    {series.length > 1 && <div className={styles.seriesControls} role="group" aria-label="Choose trajectory lines">
      <button type="button" className={selectedSeries === 'all' ? styles.activeSeriesControl : ''} aria-pressed={selectedSeries === 'all'} onClick={() => setSelectedSeries('all')}>All lines</button>
      {series.map(item => <button type="button" key={item.label} className={selectedSeries === item.label ? styles.activeSeriesControl : ''} aria-pressed={selectedSeries === item.label} onClick={() => setSelectedSeries(item.label)}><i style={{ background: item.color }} />{item.label}</button>)}
    </div>}
    <div className={styles.legend}>{series.map(item => <span key={item.label}><i style={{ background: item.color }} />{item.label}</span>)}</div>
    <svg className={styles.chart} viewBox="0 0 600 280" role="img" aria-label="Normalized historical portfolio trajectory">
      <line x1={left} y1={top} x2={right} y2={top} /><line x1={left} y1={middle} x2={right} y2={middle} /><line x1={left} y1={bottom} x2={right} y2={bottom} />
      <text className={styles.axisLabel} x="54" y={top + 4} textAnchor="end">{max.toFixed(2)}</text>
      <text className={styles.axisLabel} x="54" y={middle + 4} textAnchor="end">{((max + min) / 2).toFixed(2)}</text>
      <text className={styles.axisLabel} x="54" y={bottom + 4} textAnchor="end">{min.toFixed(2)}</text>
      {polylines}
      {selectedPoints && <>
        <text className={styles.axisLabel} x={left} y="258" textAnchor="start">{selectedPoints[0]?.date}</text>
        <text className={styles.axisLabel} x={right} y="258" textAnchor="end">{selectedPoints[selectedPoints.length - 1]?.date}</text>
        <text className={styles.axisTitle} x={(left + right) / 2} y="276" textAnchor="middle">Date</text>
      </>}
      <text className={styles.axisTitle} x="10" y="18">Normalized value</text>
    </svg>
  </>;
}
