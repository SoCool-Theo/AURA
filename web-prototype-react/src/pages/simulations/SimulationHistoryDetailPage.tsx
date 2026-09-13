import { useEffect, useState } from 'react';
import { getSimulationHistory } from '../../api/simulationsApi';
import { go } from '../../app/routes';
import {
  isSimulationHistoryV2,
  isSimulationHistoryV3,
  type SimulationHistoryDetailResponse,
} from '../../types/simulation';
import styles from './SimulationIntegration.module.css';
import { SimulationResults } from './components/SimulationResults';
import { formatTimestamp, historyDetailToRunResult, simulationErrorMessage } from './simulationUi';

export function SimulationHistoryDetailPage({ portfolioId, simulationId }: { portfolioId: string; simulationId: string }) {
  const [detail, setDetail] = useState<SimulationHistoryDetailResponse | null>(null); const [loading, setLoading] = useState(true); const [error, setError] = useState<string | null>(null); const [reloadKey, setReloadKey] = useState(0);
  useEffect(() => { const controller = new AbortController(); setLoading(true); setError(null); setDetail(null); void getSimulationHistory(portfolioId, simulationId, { signal: controller.signal }).then(setDetail).catch(requestError => { if (!controller.signal.aborted) setError(simulationErrorMessage(requestError, 'Unable to retrieve simulation.')); }).finally(() => { if (!controller.signal.aborted) setLoading(false); }); return () => controller.abort(); }, [portfolioId, simulationId, reloadKey]);
  if (loading) return <div className={styles.state} role="status"><h2>Loading simulation</h2><p>Retrieving the immutable saved result.</p></div>;
  if (error || !detail) return <div className={styles.state} role="alert"><h2>Simulation unavailable</h2><p>{error || 'Simulation not found'}</p><button className="primary-btn" onClick={() => setReloadKey(value => value + 1)}>Try Again</button> <button className="secondary-btn" onClick={() => go(`simulations/${portfolioId}`)}>Back to Simulations</button></div>;
  const detailV2 = isSimulationHistoryV2(detail) ? detail : null;
  const detailV3 = isSimulationHistoryV3(detail) ? detail : null;
  const portfolioLabel = detailV3
    ? 'Planned Allocation'
    : detailV2
      ? 'Current Holdings'
      : 'Legacy Allocation';
  return <div className="page simulations-page"><button className="secondary-btn" onClick={() => go(`simulations/${portfolioId}`)}>← Simulation History</button><header className={styles.detailHeader}><div><h1>Saved Simulation</h1><p>{portfolioLabel} · Created {formatTimestamp(detail.created_at)} · Simulation {detail.id}</p></div><span className={styles.badge}>Immutable Snapshot</span></header><SimulationResults result={historyDetailToRunResult(detail)} immutable baseline={detailV3?.baseline ?? detailV2?.baseline} /></div>;
}
