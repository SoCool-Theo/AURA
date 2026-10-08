import { useEffect, useState } from 'react';
import { getSimulationHistory } from '../../api/simulationsApi';
import { go } from '../../app/routes';
import { ScreenErrorState } from '../../components/ui/ApiErrorState';
import { Icon } from '../../components/ui/Icon';
import {
  isSimulationHistoryV2,
  isSimulationHistoryV3,
  type SimulationHistoryDetailResponse,
} from '../../types/simulation';
import styles from './SimulationIntegration.module.css';
import { SimulationResults } from './components/SimulationResults';
import { DeleteSimulationButton } from './components/DeleteSimulationButton';
import { formatTimestamp, historyDetailToRunResult } from './simulationUi';

export function SimulationHistoryDetailPage({ portfolioId, simulationId }: { portfolioId: string; simulationId: string }) {
  const [detail, setDetail] = useState<SimulationHistoryDetailResponse | null>(null); const [loading, setLoading] = useState(true); const [error, setError] = useState<unknown>(null); const [reloadKey, setReloadKey] = useState(0);
  useEffect(() => { const controller = new AbortController(); setLoading(true); setError(null); setDetail(null); void getSimulationHistory(portfolioId, simulationId, { signal: controller.signal }).then(setDetail).catch(requestError => { if (!controller.signal.aborted) setError(requestError); }).finally(() => { if (!controller.signal.aborted) setLoading(false); }); return () => controller.abort(); }, [portfolioId, simulationId, reloadKey]);
  if (loading) return <div className={styles.state} role="status"><h2>Loading simulation</h2><p>Retrieving the immutable saved result.</p></div>;
  if (error || !detail) return <ScreenErrorState error={error ?? 'Simulation not found.'} fallbackMessage="Unable to retrieve this simulation." resourceName="Simulation" onRetry={() => setReloadKey(value => value + 1)} onBack={() => go(`simulations/${portfolioId}`)} backTitle="Back to Simulations" />;
  const detailV2 = isSimulationHistoryV2(detail) ? detail : null;
  const detailV3 = isSimulationHistoryV3(detail) ? detail : null;
  const portfolioLabel = detailV3
    ? 'Planned Allocation'
    : detailV2
      ? 'Current Holdings'
      : 'Legacy Allocation';
  return <div className="page simulations-page"><button className="secondary-btn" onClick={() => go(`simulations/${portfolioId}`)}>← Simulation History</button><header className={styles.detailHeader}><div><h1>Saved Simulation</h1><p>{portfolioLabel} · Created {formatTimestamp(detail.created_at)} · Simulation {detail.id}</p></div><div className={styles.historyActions}><span className={styles.badge}>Immutable Snapshot</span><DeleteSimulationButton key={`${portfolioId}/${simulationId}`} portfolioId={portfolioId} simulationId={simulationId} subject={`${portfolioLabel} · ${formatTimestamp(detail.created_at)} · ${detail.id}`} onDeleted={() => go(`simulations/${portfolioId}`)} /></div></header><SimulationResults result={historyDetailToRunResult(detail)} immutable baseline={detailV3?.baseline ?? detailV2?.baseline} /><section className={`card ${styles.assistantCard}`}><div><small>NEED HELP UNDERSTANDING THE RESULT?</small><h2>Ask Aura about this saved simulation</h2><p>Aura will explain the exact immutable simulation baseline shown above.</p></div><button className="primary-btn" onClick={() => go(`assistant/${portfolioId}/simulation/${simulationId}`)}><Icon name="assistant" size={17} /> Ask Aura</button></section></div>;
}
