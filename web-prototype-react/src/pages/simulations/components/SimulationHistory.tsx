import { useEffect, useState } from 'react';
import { listSimulationHistory } from '../../../api/simulationsApi';
import { go } from '../../../app/routes';
import { InlineErrorCard } from '../../../components/ui/ApiErrorState';
import { Card } from '../../../components/ui/Card';
import type { SimulationHistorySummary } from '../../../types/simulation';
import { formatTimestamp, simulationTypeLabel } from '../simulationUi';
import styles from '../SimulationIntegration.module.css';

export function SimulationHistory({ portfolioId, reloadKey }: { portfolioId: string; reloadKey: number }) {
  const [items, setItems] = useState<SimulationHistorySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [retryKey, setRetryKey] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError(null); setItems([]);
    void listSimulationHistory(portfolioId, { signal: controller.signal }).then(response => setItems(response.simulations)).catch(requestError => { if (!controller.signal.aborted) setError(requestError); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [portfolioId, reloadKey, retryKey]);
  return <div id="simulation-history"><Card className={styles.history}><div className={styles.historyHeader}><div><h2>Simulation History</h2><p>Immutable successful runs for this portfolio, newest first.</p></div></div>
    {loading && <p role="status">Loading saved simulations…</p>}{Boolean(error) && <InlineErrorCard error={error} fallbackMessage="Unable to load simulation history." onRetry={() => setRetryKey(value => value + 1)} />}{!loading && !error && !items.length && <p>No saved simulations yet.</p>}
    {!loading && !error && items.length > 0 && <div style={{ overflowX: 'auto' }}><table className={styles.table}><thead><tr><th>Created</th><th>Type</th><th>Scenario</th><th>Requested dates</th><th /></tr></thead><tbody>{items.map(item => <tr key={item.id}><td>{formatTimestamp(item.created_at)}</td><td>{simulationTypeLabel(item.simulation_type)}</td><td>{item.scenario_id ?? 'N/A'}</td><td>{item.requested_start_date} to {item.requested_end_date}</td><td><button onClick={() => go(`simulations/${portfolioId}/${item.id}`)}>Open snapshot →</button></td></tr>)}</tbody></table></div>}
  </Card></div>;
}
