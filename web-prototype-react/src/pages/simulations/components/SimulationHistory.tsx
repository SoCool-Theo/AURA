import { useEffect, useRef, useState } from 'react';
import { DeleteSimulationButton } from './DeleteSimulationButton';
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
  const deletedIdsRef = useRef(new Set<string>());
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError(null); setItems([]);
    void listSimulationHistory(portfolioId, { signal: controller.signal }).then(response => { if (!controller.signal.aborted) setItems(response.simulations.filter(item => !deletedIdsRef.current.has(item.id))); }).catch(requestError => { if (!controller.signal.aborted) setError(requestError); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [portfolioId, reloadKey, retryKey]);
  return <div id="simulation-history"><Card className={styles.history}><div className={styles.historyHeader}><div><h2>Simulation History</h2><p>Immutable successful runs for this portfolio, newest first.</p></div></div>
    {loading && <p role="status">Loading saved simulations…</p>}{Boolean(error) && <InlineErrorCard error={error} fallbackMessage="Unable to load simulation history." onRetry={() => setRetryKey(value => value + 1)} />}{!loading && !error && !items.length && <p>No saved simulations yet.</p>}
    {!loading && !error && items.length > 0 && <div style={{ overflowX: 'auto' }}>
      <table className={`${styles.table} ${styles.historyTable}`}>
        <thead><tr><th scope="col">Created</th><th scope="col">Type</th><th scope="col">Scenario</th><th scope="col">Requested dates</th><th scope="col">Actions</th></tr></thead>
        <tbody>{items.map(item => <tr key={item.id}>
          <td>{formatTimestamp(item.created_at)}</td>
          <td>{simulationTypeLabel(item.simulation_type)}</td>
          <td>{item.scenario_id ?? 'N/A'}</td>
          <td>{item.requested_start_date} to {item.requested_end_date}</td>
          <td><div className={styles.historyActions}>
            <button onClick={() => go(`simulations/${portfolioId}/${item.id}`)}>Open snapshot →</button>
            <DeleteSimulationButton portfolioId={portfolioId} simulationId={item.id} subject={`${simulationTypeLabel(item.simulation_type)} · ${formatTimestamp(item.created_at)} · ${item.id}`} onDeleted={() => { deletedIdsRef.current.add(item.id); setItems(current => current.filter(row => row.id !== item.id)); }} />
          </div></td>
        </tr>)}</tbody>
      </table>
    </div>}
  </Card></div>;
}
