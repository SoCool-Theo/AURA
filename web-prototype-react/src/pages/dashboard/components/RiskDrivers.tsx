import type { RiskDriverEntry } from '../../../types/analytics';
import { go } from '../../../app/routes';
import { Card } from '../../../components/ui/Card';
import { SymbolBadge } from '../../../components/ui/SymbolBadge';
import { formatPercent } from '../dashboardUi';
import styles from '../DashboardIntegration.module.css';

export function RiskDrivers({ portfolioId, reportId, drivers, loading, failed }: { portfolioId: string; reportId: string | null; drivers: RiskDriverEntry[] | null; loading: boolean; failed: boolean }) {
  return <Card className="dashboard-risk-card"><div className="dashboard-card-header"><div className="dashboard-card-title"><h2>Top Risk Drivers</h2></div><button className="text-btn" onClick={() => go(`analytics/${portfolioId}`)}>View analysis <span aria-hidden="true">→</span></button></div>
    {loading && <div className={styles.emptyPanel}><p role="status">Loading risk drivers…</p></div>}
    {!loading && !drivers && <div className={styles.emptyPanel}><h3>{failed ? 'Risk drivers unavailable' : 'Not analyzed'}</h3><p>{failed ? 'The latest report could not be retrieved.' : 'Create an analysis to identify portfolio risk drivers.'}</p></div>}
    {!loading && drivers && !drivers.length && <div className={styles.emptyPanel}><h3>No risk drivers</h3><p>The latest report returned no risk-driver entries.</p></div>}
    {!loading && drivers && drivers.length > 0 && <div className="dashboard-risk-list">{drivers.slice(0, 3).map(driver => <button type="button" className={styles.driverRow} key={`${driver.rank}-${driver.symbol}`} onClick={() => reportId && go(`asset/${portfolioId}/${reportId}/${encodeURIComponent(driver.symbol)}`)} disabled={!reportId} aria-label={`Open ${driver.symbol} asset risk details`}>
      <SymbolBadge symbol={driver.symbol} />
      <div className={styles.driverIdentity}>
        <div><span>#{driver.rank}</span><strong>{driver.symbol}</strong></div>
        <small>{formatPercent(driver.weight)} portfolio weight</small>
      </div>
      <div className={styles.driverValue}>
        <small>Volatility contribution</small>
        <strong className={driver.percentage_volatility_contribution < 0 ? styles.negative : ''}>{formatPercent(driver.percentage_volatility_contribution)}</strong>
      </div>
      <div className={styles.driverTrack} aria-hidden="true"><span style={{ width: `${Math.min(100, Math.abs(driver.percentage_volatility_contribution * 100))}%` }} /></div>
      <span className={styles.driverChevron} aria-hidden="true">›</span>
    </button>)}</div>}
  </Card>;
}
