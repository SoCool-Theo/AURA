import type { PortfolioReturnPoint } from '../../../types/analytics';
import styles from '../DashboardIntegration.module.css';

export function PortfolioReturnChart({ points }: { points: PortfolioReturnPoint[] }) {
  if (!points.length) return null;
  const values = points.map(point => point.portfolio_return);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const lastIndex = Math.max(points.length - 1, 1);
  const coordinates = points.map((point, index) => {
    const x = 16 + (index / lastIndex) * 668;
    const y = 208 - ((point.portfolio_return - min) / range) * 184;
    return `${x},${y}`;
  }).join(' ');
  const middle = points[Math.floor((points.length - 1) / 2)];
  return <><svg className={styles.chart} viewBox="0 0 700 230" preserveAspectRatio="none" role="img" aria-label="Backend-returned periodic portfolio returns"><line x1="16" y1="24" x2="684" y2="24" /><line x1="16" y1="116" x2="684" y2="116" /><line x1="16" y1="208" x2="684" y2="208" /><polyline points={coordinates} /></svg><div className={styles.chartLabels}><span>{points[0].date}</span>{middle && <span>{middle.date}</span>}<span>{points[points.length - 1].date}</span></div></>;
}
