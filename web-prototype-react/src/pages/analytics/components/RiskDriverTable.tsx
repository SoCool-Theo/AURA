import { Card } from '../../../components/ui/Card';
import type { RiskDriverAnalysis } from '../../../types/analytics';
import { formatPercent } from '../analyticsUi';
import styles from '../AnalyticsIntegration.module.css';

interface RiskDriverTableProps {
  riskDrivers: RiskDriverAnalysis;
}

export function RiskDriverTable({ riskDrivers }: RiskDriverTableProps) {
  return (
    <Card className={styles.section}>
      <div className={styles.sectionHeading}>
        <div><h2>Risk Drivers</h2><p>Ranked contributors to the portfolio's historical volatility.</p></div>
        <span className={styles.badge}>Top driver: {riskDrivers.top_driver}</span>
      </div>
      <div className={styles.tableWrap}>
        <table className={styles.dataTable}>
          <thead><tr><th>Rank</th><th>Symbol</th><th>Weight</th><th>Asset volatility</th><th>Marginal contribution</th><th>Component contribution</th><th>Portfolio contribution</th></tr></thead>
          <tbody>{riskDrivers.entries.map(driver => (
            <tr key={driver.symbol}>
              <td>{driver.rank}</td>
              <td><strong>{driver.symbol}</strong></td>
              <td>{formatPercent(driver.weight)}</td>
              <td>{formatPercent(driver.annualized_asset_volatility)}</td>
              <td className={driver.marginal_volatility_contribution < 0 ? styles.signedNegative : ''}>{formatPercent(driver.marginal_volatility_contribution)}</td>
              <td className={driver.component_volatility_contribution < 0 ? styles.signedNegative : ''}>{formatPercent(driver.component_volatility_contribution)}</td>
              <td className={driver.percentage_volatility_contribution < 0 ? styles.signedNegative : ''}>{formatPercent(driver.percentage_volatility_contribution)}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </Card>
  );
}
