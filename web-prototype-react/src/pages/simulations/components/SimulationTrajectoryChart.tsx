import type { HistoricalScenarioTrajectoryPoint } from '../../../types/simulation';
import styles from '../SimulationIntegration.module.css';

interface Series { label: string; color: string; points: HistoricalScenarioTrajectoryPoint[] }

export function SimulationTrajectoryChart({ series }: { series: Series[] }) {
  const values = series.flatMap(item => item.points.map(point => point.normalized_value));
  if (!values.length) return <p>No trajectory observations were returned.</p>;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const polylines = series.map(item => {
    const lastIndex = Math.max(item.points.length - 1, 1);
    const points = item.points.map((point, index) => {
      const x = 18 + (index / lastIndex) * 564;
      const y = 232 - ((point.normalized_value - min) / range) * 204;
      return `${x},${y}`;
    }).join(' ');
    return <polyline key={item.label} points={points} stroke={item.color} />;
  });

  return <>
    <div className={styles.legend}>{series.map(item => <span key={item.label}><i style={{ background: item.color }} />{item.label}</span>)}</div>
    <svg className={styles.chart} viewBox="0 0 600 260" role="img" aria-label="Normalized historical portfolio trajectory">
      <line x1="18" y1="28" x2="582" y2="28" /><line x1="18" y1="130" x2="582" y2="130" /><line x1="18" y1="232" x2="582" y2="232" />
      {polylines}
    </svg>
  </>;
}
