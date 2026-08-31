import type { RiskDriverEntry } from '../../../types/analytics';
import { go } from '../../../app/routes';
import { Card } from '../../../components/ui/Card';
import { SymbolBadge } from '../../../components/ui/SymbolBadge';
import { formatPercent } from '../dashboardUi';
import styles from '../DashboardIntegration.module.css';

export function RiskDrivers({ portfolioId, drivers, loading, failed }: { portfolioId: string; drivers: RiskDriverEntry[] | null; loading: boolean; failed: boolean }) {
  return <Card className="dashboard-risk-card"><div className="dashboard-card-header"><div className="dashboard-card-title"><h2>Top Risk Drivers</h2></div><button className="text-btn" onClick={() => go(`analytics/${portfolioId}`)}>View analysis</button></div>
    {loading && <div className={styles.emptyPanel}><p role="status">Loading risk drivers…</p></div>}
    {!loading && !drivers && <div className={styles.emptyPanel}><h3>{failed ? 'Risk drivers unavailable' : 'Not analyzed'}</h3><p>{failed ? 'The latest report could not be retrieved.' : 'Create an analysis to identify portfolio risk drivers.'}</p></div>}
    {!loading && drivers && !drivers.length && <div className={styles.emptyPanel}><h3>No risk drivers</h3><p>The latest report returned no risk-driver entries.</p></div>}
    {!loading && drivers && drivers.length > 0 && <div className="dashboard-risk-list">{drivers.slice(0, 3).map(driver => <div key={`${driver.rank}-${driver.symbol}`}><SymbolBadge symbol={driver.symbol} /><div><strong>#{driver.rank} {driver.symbol}</strong><small>{formatPercent(driver.weight)} portfolio weight</small></div><div className={styles.driverValue}><small>Volatility contribution</small><strong className={driver.percentage_volatility_contribution < 0 ? styles.negative : ''}>{formatPercent(driver.percentage_volatility_contribution)}</strong></div></div>)}</div>}
  </Card>;
}
