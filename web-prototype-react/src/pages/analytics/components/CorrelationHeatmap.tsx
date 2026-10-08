import { Card } from '../../../components/ui/Card';
import type { CorrelationMatrixResponse, CorrelationPair } from '../../../types/analytics';
import { formatNumber } from '../analyticsUi';
import styles from '../AnalyticsIntegration.module.css';

interface CorrelationHeatmapProps {
  matrix: CorrelationMatrixResponse;
  pairs: CorrelationPair[];
}

export function CorrelationHeatmap({ matrix, pairs }: CorrelationHeatmapProps) {
  return (
    <Card className={styles.section}>
      <div className={styles.sectionHeading}>
        <div><h2>Asset Correlations</h2><p>Nullable values remain unavailable rather than becoming zero.</p></div>
        <span className={styles.badge}>{pairs.length} defined pair records</span>
      </div>
      <div className={styles.tableWrap} role="region" aria-label="Asset correlation matrix" tabIndex={0}>
        <table className={styles.matrix}>
          <thead><tr><th aria-label="Asset" />{matrix.symbols.map(symbol => <th key={symbol}>{symbol}</th>)}</tr></thead>
          <tbody>{matrix.values.map((row, rowIndex) => (
            <tr key={matrix.symbols[rowIndex]}>
              <th scope="row">{matrix.symbols[rowIndex]}</th>
              {row.map((value, columnIndex) => (
                <td key={matrix.symbols[columnIndex]} className={value === null ? styles.nullCell : ''}>
                  {formatNumber(value)}
                </td>
              ))}
            </tr>
          ))}</tbody>
        </table>
      </div>
      {pairs.length > 0 && <div className={styles.tableWrap}>
        <table className={styles.dataTable}>
          <thead><tr><th>Asset A</th><th>Asset B</th><th>Correlation</th></tr></thead>
          <tbody>{pairs.map(pair => (
            <tr key={`${pair.asset_a}/${pair.asset_b}`}><td><strong>{pair.asset_a}</strong></td><td><strong>{pair.asset_b}</strong></td><td>{formatNumber(pair.correlation)}</td></tr>
          ))}</tbody>
        </table>
      </div>}
    </Card>
  );
}
