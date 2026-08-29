import type { AllocationSimulationResult, HistoricalScenarioMetrics, HistoricalScenarioTrajectoryPoint, SimulationRunResult } from '../../../types/simulation';
import { Card } from '../../../components/ui/Card';
import { formatNumber, formatPercent } from '../simulationUi';
import styles from '../SimulationIntegration.module.css';
import { SimulationComparison } from './SimulationComparison';
import { SimulationTrajectoryChart } from './SimulationTrajectoryChart';

function Metrics({ metrics }: { metrics: HistoricalScenarioMetrics }) {
  const drawdown = metrics.maximum_drawdown;
  return <div className={styles.metrics}>
    <Card className={styles.metric}><small>Cumulative Return</small><strong className={metrics.cumulative_return < 0 ? styles.negative : ''}>{formatPercent(metrics.cumulative_return)}</strong><span>Backend result</span></Card>
    <Card className={styles.metric}><small>Ending Normalized Value</small><strong>{formatNumber(metrics.normalized_ending_value)}</strong><span>Started at {formatNumber(metrics.normalized_starting_value)}</span></Card>
    <Card className={styles.metric}><small>Annualized Volatility</small><strong>{formatPercent(metrics.annualized_volatility)}</strong><span>Backend result</span></Card>
    <Card className={styles.metric}><small>Sharpe Ratio</small><strong>{formatNumber(metrics.sharpe_ratio)}</strong><span>Nullable backend value</span></Card>
    <Card className={styles.metric}><small>Maximum Drawdown</small><strong className={drawdown.max_drawdown < 0 ? styles.negative : ''}>{formatPercent(drawdown.max_drawdown)}</strong><span>{drawdown.peak_date ?? 'N/A'} to {drawdown.trough_date ?? 'N/A'}</span></Card>
  </div>;
}

function Allocation({ title, result }: { title: string; result: AllocationSimulationResult }) {
  return <Card className={styles.panel}><h3>{title}</h3><div className={styles.allocationList}>{result.allocation.map(item => <span key={item.symbol}>{item.symbol} {formatPercent(item.weight, 4)}</span>)}</div></Card>;
}

function Trajectories({ original, modified }: { original: HistoricalScenarioTrajectoryPoint[]; modified?: HistoricalScenarioTrajectoryPoint[] }) {
  const series = [{ label: modified ? 'Original' : 'Portfolio', color: '#35d7c0', points: original }];
  if (modified) series.push({ label: 'Modified', color: '#8c78ff', points: modified });
  return <Card className={styles.panel}><h3>Normalized Trajectory</h3><p>Visualization of the observations returned by the backend; no financial series is recreated in the browser.</p><SimulationTrajectoryChart series={series} /></Card>;
}

function Metadata({ requestedStart, requestedEnd, effectiveStart, effectiveEnd, priceCount, returnCount }: { requestedStart: string; requestedEnd: string; effectiveStart: string; effectiveEnd: string; priceCount: number; returnCount: number }) {
  return <Card className={styles.panel}><h3>Simulation Dates</h3><p>Requested and effective periods remain distinct.</p><dl className={styles.details}><div><dt>Requested start</dt><dd>{requestedStart}</dd></div><div><dt>Requested end</dt><dd>{requestedEnd}</dd></div><div><dt>Effective start</dt><dd>{effectiveStart}</dd></div><div><dt>Effective end</dt><dd>{effectiveEnd}</dd></div><div><dt>Price observations</dt><dd>{priceCount}</dd></div><div><dt>Return observations</dt><dd>{returnCount}</dd></div></dl></Card>;
}

export function SimulationResults({ result, immutable = false }: { result: SimulationRunResult; immutable?: boolean }) {
  if (result.type === 'historical-scenario') {
    const response = result.response; const metadata = response.metadata;
    return <section className="simulation-results"><div className="simulation-results-heading"><div><span>SIMULATION RESULTS</span><h2>{response.scenario.display_name}</h2><p>{response.portfolio_name} · Historical Scenario{immutable ? ' · Immutable snapshot' : ''}</p></div><span className="results-status"><i /> Completed</span></div><Metrics metrics={response.metrics} /><div className={styles.resultGrid}><Trajectories original={response.trajectory} /><Metadata requestedStart={response.scenario.requested_start_date} requestedEnd={response.scenario.requested_end_date} effectiveStart={metadata.effective_start_date} effectiveEnd={metadata.effective_end_date} priceCount={metadata.price_observation_count} returnCount={metadata.return_observation_count} /></div><Card className={styles.panel}><h3>{response.scenario.display_name}</h3><p>{response.scenario.description}</p></Card></section>;
  }
  if (result.type === 'allocation') {
    const response = result.response; const metadata = response.metadata;
    return <section className="simulation-results"><div className="simulation-results-heading"><div><span>SIMULATION RESULTS</span><h2>Allocation Change</h2><p>{response.portfolio_name} · Allocation Change{immutable ? ' · Immutable snapshot' : ''}</p></div><span className="results-status"><i /> Completed</span></div><h3>Original allocation metrics</h3><Metrics metrics={response.original.metrics} /><h3>Modified allocation metrics</h3><Metrics metrics={response.modified.metrics} /><div className={styles.resultGrid}><Trajectories original={response.original.trajectory} modified={response.modified.trajectory} /><Metadata requestedStart={response.start_date} requestedEnd={response.end_date} effectiveStart={metadata.effective_start_date} effectiveEnd={metadata.effective_end_date} priceCount={metadata.price_observation_count} returnCount={metadata.return_observation_count} /></div><div className={styles.resultGrid}><Allocation title="Original Allocation" result={response.original} /><Allocation title="Modified Allocation" result={response.modified} /></div><SimulationComparison comparison={response.comparison} /></section>;
  }
  const response = result.response; const metadata = response.metadata;
  return <section className="simulation-results"><div className="simulation-results-heading"><div><span>SIMULATION RESULTS</span><h2>{response.scenario.display_name}</h2><p>{response.portfolio_name} · Combined Simulation{immutable ? ' · Immutable snapshot' : ''}</p></div><span className="results-status"><i /> Completed</span></div><h3>Original allocation metrics</h3><Metrics metrics={response.original.metrics} /><h3>Modified allocation metrics</h3><Metrics metrics={response.modified.metrics} /><div className={styles.resultGrid}><Trajectories original={response.original.trajectory} modified={response.modified.trajectory} /><Metadata requestedStart={response.scenario.requested_start_date} requestedEnd={response.scenario.requested_end_date} effectiveStart={metadata.effective_start_date} effectiveEnd={metadata.effective_end_date} priceCount={metadata.price_observation_count} returnCount={metadata.return_observation_count} /></div><div className={styles.resultGrid}><Allocation title="Original Allocation" result={response.original} /><Allocation title="Modified Allocation" result={response.modified} /></div><SimulationComparison comparison={response.comparison} /><Card className={styles.panel}><h3>{response.scenario.display_name}</h3><p>{response.scenario.description}</p></Card></section>;
}
