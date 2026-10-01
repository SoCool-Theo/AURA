import type { PlannedPortfolioBaselineContext, PortfolioHoldingInput } from '../../../types/portfolio';
import type { PortfolioReportResponse } from '../../../types/report';
import type {
  AllocationSimulationResult,
  HistoricalScenarioMetrics,
  HistoricalScenarioTrajectoryPoint,
  SimulationBaselineValuationContext,
  SimulationRunResult,
} from '../../../types/simulation';
import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';
import {
  formatPortfolioAllocation,
  formatPortfolioMoney,
  formatPortfolioQuantity,
} from '../../portfolios/portfolioUi';
import {
  formatNumber,
  formatPercent,
  formatTimestamp,
  savedAnalysisTrajectory,
} from '../simulationUi';
import styles from '../SimulationIntegration.module.css';
import { SimulationComparison } from './SimulationComparison';
import { SimulationTrajectoryChart } from './SimulationTrajectoryChart';

type MetricTone = 'success' | 'warning' | 'danger' | 'blue';

function MetricLabel({ icon, label, tone }: { icon: string; label: string; tone: MetricTone }) {
  const toneClass = {
    success: styles.successIcon,
    warning: styles.warningIcon,
    danger: styles.dangerIcon,
    blue: styles.blueIcon,
  }[tone];
  return <small className={styles.metricLabel}><i className={`${styles.metricIcon} ${toneClass}`}><Icon name={icon} size={17} /></i>{label}</small>;
}

function Metrics({ metrics }: { metrics: HistoricalScenarioMetrics }) {
  const drawdown = metrics.maximum_drawdown;
  return <div className={styles.metrics}>
    <Card className={styles.metric}><MetricLabel icon="trend" label="Cumulative Return" tone={metrics.cumulative_return < 0 ? 'danger' : 'success'} /><strong className={metrics.cumulative_return < 0 ? styles.negative : ''}>{formatPercent(metrics.cumulative_return)}</strong><span>Historical result</span></Card>
    <Card className={styles.metric}><MetricLabel icon="wallet" label="Ending Normalized Value" tone="blue" /><strong>{formatNumber(metrics.normalized_ending_value)}</strong><span>Started at {formatNumber(metrics.normalized_starting_value)}</span></Card>
    <Card className={styles.metric}><MetricLabel icon="pulse" label="Annualized Volatility" tone="warning" /><strong>{formatPercent(metrics.annualized_volatility)}</strong><span>Historical result</span></Card>
    <Card className={styles.metric}><MetricLabel icon="stats-chart" label="Sharpe Ratio" tone="blue" /><strong>{formatNumber(metrics.sharpe_ratio)}</strong><span>Risk-adjusted return metric</span></Card>
    <Card className={styles.metric}><MetricLabel icon="drawdown" label="Maximum Drawdown" tone="danger" /><strong className={drawdown.max_drawdown < 0 ? styles.negative : ''}>{formatPercent(drawdown.max_drawdown)}</strong><span>{drawdown.peak_date ?? 'N/A'} to {drawdown.trough_date ?? 'N/A'}</span></Card>
  </div>;
}

function Allocation({ title, result }: { title: string; result: AllocationSimulationResult }) {
  return <Card className={styles.panel}><h3>{title}</h3><div className={styles.allocationList}>{result.allocation.map(item => <span key={item.symbol}>{item.symbol} {formatPercent(item.weight, 4)}</span>)}</div></Card>;
}

function allocationFromBaseline(
  baseline?: SimulationBaselineValuationContext | PlannedPortfolioBaselineContext,
): PortfolioHoldingInput[] {
  if (!baseline) return [];
  if ('portfolio_type' in baseline) {
    return baseline.holdings.map(holding => ({
      symbol: holding.symbol,
      weight: Number(holding.target_allocation),
    }));
  }
  return baseline.holdings.map(holding => ({
    symbol: holding.symbol,
    weight: Number(holding.current_allocation),
  }));
}

function HistoricalComparison({
  scenarioName,
  metrics,
  allocation,
  latestAnalysis,
  latestAnalysisStatus,
  latestAnalysisError,
  onViewLatestAnalysis,
  immutable,
}: {
  scenarioName: string;
  metrics: HistoricalScenarioMetrics;
  allocation: PortfolioHoldingInput[];
  latestAnalysis?: PortfolioReportResponse | null;
  latestAnalysisStatus?: 'idle' | 'loading' | 'ready' | 'error';
  latestAnalysisError?: unknown;
  onViewLatestAnalysis?: () => void;
  immutable?: boolean;
}) {
  const reference = latestAnalysis?.analysis;
  const rows = [
    ['Cumulative return', reference ? formatPercent(reference.portfolio_metrics.cumulative_return) : 'Unavailable', formatPercent(metrics.cumulative_return)],
    ['Annualized volatility', reference ? formatPercent(reference.portfolio_metrics.annualized_volatility) : 'Unavailable', formatPercent(metrics.annualized_volatility)],
    ['Sharpe ratio', reference ? formatNumber(reference.portfolio_metrics.sharpe_ratio) : 'Unavailable', formatNumber(metrics.sharpe_ratio)],
    ['Maximum drawdown', reference ? formatPercent(reference.max_drawdown.max_drawdown) : 'Unavailable', formatPercent(metrics.maximum_drawdown.max_drawdown)],
  ];
  return <Card className="simulation-comparison-card">
    <div className="simulation-card-heading"><div><h2>Latest Portfolio Analysis vs Historical Scenario</h2><p>The reference uses the newest saved analysis for this portfolio. Both columns show backend-calculated metrics; their historical periods may be different.</p></div></div>
    <div className={styles.referenceContext}>
      {latestAnalysisStatus === 'loading' && <p role="status">Loading the latest saved portfolio analysis…</p>}
      {latestAnalysisStatus === 'error' && <p>Latest analysis details could not be loaded. The historical scenario result is still valid.{latestAnalysisError instanceof Error && latestAnalysisError.message ? ` ${latestAnalysisError.message}` : ''}</p>}
      {latestAnalysisStatus === 'ready' && !latestAnalysis && <p>No saved portfolio analysis exists yet, so Aura cannot show an original analysis reference.</p>}
      {immutable && latestAnalysisStatus === undefined && !latestAnalysis && <p>This immutable simulation snapshot does not contain a latest-analysis reference. Run a new historical scenario to compare against the portfolio’s current latest saved analysis.</p>}
      {latestAnalysis && <><div><span>Latest analysis saved</span><strong>{formatTimestamp(latestAnalysis.created_at)}</strong></div><div><span>Analysis period</span><strong>{reference?.start_date} to {reference?.end_date}</strong></div>{onViewLatestAnalysis && <button type="button" className="secondary-btn" onClick={onViewLatestAnalysis}>View latest analysis details</button>}</>}
    </div>
    <div className={styles.historicalMetricsComparison}>
      <div className={styles.historicalMetricsHeader}><strong>Metric</strong><strong>Latest analysis</strong><strong>{scenarioName}</strong></div>
      {rows.map(([label, original, scenario]) => <div className={styles.historicalMetricsRow} key={label}><span>{label}</span><strong>{original}</strong><strong>{scenario}</strong></div>)}
    </div>
    <p className={styles.referenceNote}>The latest analysis is a saved reference, not a rerun over the scenario dates. The chart normalizes each saved path to 1.00 and compares progress across each path’s own observations.</p>
    {allocation.length > 0 && <><h3>Allocation used by this scenario run</h3><div className={styles.allocationList}>{allocation.map(item => <span key={item.symbol}>{item.symbol} {formatPercent(item.weight, 4)}</span>)}</div></>}
  </Card>;
}

function Trajectories({ original, modified }: { original: HistoricalScenarioTrajectoryPoint[]; modified?: HistoricalScenarioTrajectoryPoint[] }) {
  const series = [{ label: modified ? 'Original' : 'Portfolio', color: '#31D6CF', points: original }];
  if (modified) series.push({ label: 'Modified', color: '#8B5CF6', points: modified });
  return <Card className={styles.panel}><h3>Normalized Trajectory</h3><p>Historical value path normalized to a starting value of 1.00.</p><SimulationTrajectoryChart series={series} /></Card>;
}

function HistoricalTrajectories({
  scenario,
  latestAnalysis,
}: {
  scenario: HistoricalScenarioTrajectoryPoint[];
  latestAnalysis?: PortfolioReportResponse | null;
}) {
  const series = latestAnalysis ? [{
    label: 'Latest analysis',
    color: '#94A3B8',
    points: savedAnalysisTrajectory(latestAnalysis.analysis),
  }] : [];
  series.push({ label: 'Historical scenario', color: '#31D6CF', points: scenario });
  return <Card className={styles.panel}><h3>Latest Analysis vs Historical Scenario</h3><p>Select one line for its own date and value axes. All lines share only the normalized-value labels because the saved periods can differ.</p><SimulationTrajectoryChart series={series} /></Card>;
}

function LatestAnalysisReference({
  latestAnalysis,
  latestAnalysisStatus,
  latestAnalysisError,
  onViewLatestAnalysis,
  immutable,
}: {
  latestAnalysis?: PortfolioReportResponse | null;
  latestAnalysisStatus?: 'idle' | 'loading' | 'ready' | 'error';
  latestAnalysisError?: unknown;
  onViewLatestAnalysis?: () => void;
  immutable?: boolean;
}) {
  const analysis = latestAnalysis?.analysis;
  return <Card className={styles.panel}>
    <h3>Latest Saved Portfolio Analysis</h3>
    <p>This is additional saved context. The allocation comparison below still uses Aura’s backend original and modified results over the same requested period.</p>
    <div className={styles.referenceContext}>
      {latestAnalysisStatus === 'loading' && <p role="status">Loading the latest saved portfolio analysis…</p>}
      {latestAnalysisStatus === 'error' && <p>Latest analysis details could not be loaded. The allocation comparison is still valid.{latestAnalysisError instanceof Error && latestAnalysisError.message ? ` ${latestAnalysisError.message}` : ''}</p>}
      {latestAnalysisStatus === 'ready' && !latestAnalysis && <p>No saved portfolio analysis exists yet. Run an analysis to create this additional reference.</p>}
      {immutable && latestAnalysisStatus === undefined && !latestAnalysis && <p>This immutable simulation snapshot does not contain a latest-analysis reference. Run a new simulation comparison to use the portfolio’s current latest saved analysis.</p>}
      {latestAnalysis && <><div><span>Latest analysis saved</span><strong>{formatTimestamp(latestAnalysis.created_at)}</strong></div><div><span>Analysis period</span><strong>{analysis?.start_date} to {analysis?.end_date}</strong></div>{onViewLatestAnalysis && <button type="button" className="secondary-btn" onClick={onViewLatestAnalysis}>View latest analysis details</button>}</>}
    </div>
    {analysis && <div className={styles.referenceMetricGrid}>
      <div><span>Cumulative return</span><strong>{formatPercent(analysis.portfolio_metrics.cumulative_return)}</strong></div>
      <div><span>Annualized volatility</span><strong>{formatPercent(analysis.portfolio_metrics.annualized_volatility)}</strong></div>
      <div><span>Sharpe ratio</span><strong>{formatNumber(analysis.portfolio_metrics.sharpe_ratio)}</strong></div>
      <div><span>Maximum drawdown</span><strong>{formatPercent(analysis.max_drawdown.max_drawdown)}</strong></div>
    </div>}
  </Card>;
}

function CombinedLatestAnalysisComparison({
  metrics,
  latestAnalysis,
  latestAnalysisStatus,
  latestAnalysisError,
  onViewLatestAnalysis,
  immutable,
}: {
  metrics: HistoricalScenarioMetrics;
  latestAnalysis?: PortfolioReportResponse | null;
  latestAnalysisStatus?: 'idle' | 'loading' | 'ready' | 'error';
  latestAnalysisError?: unknown;
  onViewLatestAnalysis?: () => void;
  immutable?: boolean;
}) {
  const reference = latestAnalysis?.analysis;
  const rows = [
    ['Cumulative return', reference ? formatPercent(reference.portfolio_metrics.cumulative_return) : 'Unavailable', formatPercent(metrics.cumulative_return)],
    ['Annualized volatility', reference ? formatPercent(reference.portfolio_metrics.annualized_volatility) : 'Unavailable', formatPercent(metrics.annualized_volatility)],
    ['Sharpe ratio', reference ? formatNumber(reference.portfolio_metrics.sharpe_ratio) : 'Unavailable', formatNumber(metrics.sharpe_ratio)],
    ['Maximum drawdown', reference ? formatPercent(reference.max_drawdown.max_drawdown) : 'Unavailable', formatPercent(metrics.maximum_drawdown.max_drawdown)],
  ];
  return <Card className="simulation-comparison-card">
    <div className="simulation-card-heading"><div><h2>Latest Portfolio Analysis vs New Combined Simulation</h2><p>The new combined result is the modified allocation under the selected historical scenario. Both columns are backend-calculated; their historical periods may be different.</p></div></div>
    <div className={styles.referenceContext}>
      {latestAnalysisStatus === 'loading' && <p role="status">Loading the latest saved portfolio analysis…</p>}
      {latestAnalysisStatus === 'error' && <p>Latest analysis details could not be loaded. The combined simulation result is still valid.{latestAnalysisError instanceof Error && latestAnalysisError.message ? ` ${latestAnalysisError.message}` : ''}</p>}
      {latestAnalysisStatus === 'ready' && !latestAnalysis && <p>No saved portfolio analysis exists yet, so Aura cannot show the requested comparison.</p>}
      {immutable && latestAnalysisStatus === undefined && !latestAnalysis && <p>This immutable simulation snapshot does not contain a latest-analysis reference. Run a new combined simulation to compare against the portfolio’s current latest saved analysis.</p>}
      {latestAnalysis && <><div><span>Latest analysis saved</span><strong>{formatTimestamp(latestAnalysis.created_at)}</strong></div><div><span>Analysis period</span><strong>{reference?.start_date} to {reference?.end_date}</strong></div>{onViewLatestAnalysis && <button type="button" className="secondary-btn" onClick={onViewLatestAnalysis}>View latest analysis details</button>}</>}
    </div>
    <div className={styles.historicalMetricsComparison}>
      <div className={styles.historicalMetricsHeader}><strong>Metric</strong><strong>Latest analysis</strong><strong>New combined result</strong></div>
      {rows.map(([label, original, combined]) => <div className={styles.historicalMetricsRow} key={label}><span>{label}</span><strong>{original}</strong><strong>{combined}</strong></div>)}
    </div>
    <p className={styles.referenceNote}>The latest analysis remains a saved reference; it is not recalculated over the combined scenario dates.</p>
  </Card>;
}

function CombinedLatestAnalysisTrajectories({
  combined,
  latestAnalysis,
}: {
  combined: HistoricalScenarioTrajectoryPoint[];
  latestAnalysis: PortfolioReportResponse;
}) {
  return <Card className={styles.panel}><h3>Latest Analysis vs New Combined Simulation</h3><p>Select one line for its own date and value axes. All lines share only normalized-value labels because the saved periods can differ.</p><SimulationTrajectoryChart series={[
    { label: 'Latest analysis', color: '#94A3B8', points: savedAnalysisTrajectory(latestAnalysis.analysis) },
    { label: 'New combined result', color: '#31D6CF', points: combined },
  ]} /></Card>;
}

function Baseline({ baseline }: {
  baseline: SimulationBaselineValuationContext | PlannedPortfolioBaselineContext;
}) {
  if ('portfolio_type' in baseline) {
    return <Card className={[styles.panel, styles.plannedBaseline].join(' ')}>
      <div className={styles.baselineHeading}><div><small>SAVED PLANNED ALLOCATION</small><h3>{formatPortfolioMoney(baseline.total_proposed_amount, baseline.plan_currency)}</h3></div><span className={styles.badge}>{baseline.plan_currency}</span></div>
      <p>{baseline.hypothetical_notice}</p>
      <div className={styles.baselineRows}>{baseline.holdings.map(holding => <div key={holding.id}><strong>{holding.symbol}</strong><span>Proposed {formatPortfolioMoney(holding.proposed_amount, baseline.plan_currency)}</span><b>{formatPortfolioAllocation(holding.target_allocation)}</b></div>)}</div>
      <p className={styles.baselineNote}>Target weights come from proposed amounts. Estimated shares do not affect this simulation.</p>
    </Card>;
  }
  return <Card className={[styles.panel, styles.currentBaseline].join(' ')}>
    <div className={styles.baselineHeading}><div><small>SAVED CURRENT VALUATION</small><h3>{formatPortfolioMoney(baseline.total_current_value_usd, 'USD')}</h3></div><span className={styles.badge}>USD</span></div>
    <p>Valued {baseline.valuation_date} using prices dated {baseline.oldest_price_as_of} through {baseline.newest_price_as_of}. These values are not updated.</p>
    <div className={styles.baselineRows}>{baseline.holdings.map(holding => <div key={holding.position + '-' + holding.symbol}><strong>{holding.symbol}</strong><span>{formatPortfolioQuantity(holding.shares)} shares · {formatPortfolioMoney(holding.asset_price, 'USD')}</span><b>{formatPortfolioMoney(holding.current_value_usd, 'USD')} · {formatPortfolioAllocation(holding.current_allocation)}</b></div>)}</div>
  </Card>;
}

function Metadata({ requestedStart, requestedEnd, effectiveStart, effectiveEnd, priceCount, returnCount }: { requestedStart: string; requestedEnd: string; effectiveStart: string; effectiveEnd: string; priceCount: number; returnCount: number }) {
  return <Card className={styles.panel}><h3>Simulation Dates</h3><p>Requested and effective periods remain distinct.</p><dl className={styles.details}><div><dt>Requested start</dt><dd>{requestedStart}</dd></div><div><dt>Requested end</dt><dd>{requestedEnd}</dd></div><div><dt>Effective start</dt><dd>{effectiveStart}</dd></div><div><dt>Effective end</dt><dd>{effectiveEnd}</dd></div><div><dt>Price observations</dt><dd>{priceCount}</dd></div><div><dt>Return observations</dt><dd>{returnCount}</dd></div></dl></Card>;
}

export function SimulationResults({ result, immutable = false, baseline, originalAllocation, latestAnalysis, latestAnalysisStatus, latestAnalysisError, onViewLatestAnalysis }: { result: SimulationRunResult; immutable?: boolean; baseline?: SimulationBaselineValuationContext | PlannedPortfolioBaselineContext; originalAllocation?: PortfolioHoldingInput[]; latestAnalysis?: PortfolioReportResponse | null; latestAnalysisStatus?: 'idle' | 'loading' | 'ready' | 'error'; latestAnalysisError?: unknown; onViewLatestAnalysis?: () => void }) {
  if (result.type === 'historical-scenario') {
    const response = result.response; const metadata = response.metadata;
    const comparisonAllocation = originalAllocation ?? allocationFromBaseline(baseline);
    return <section className="simulation-results"><div className="simulation-results-heading"><div><span>SIMULATION RESULTS</span><h2>{response.scenario.display_name}</h2><p>{response.portfolio_name} · Historical Scenario{immutable ? ' · Immutable snapshot' : ''}</p></div><span className="results-status"><i /> Completed</span></div>{baseline && <Baseline baseline={baseline} />}<HistoricalComparison scenarioName={response.scenario.display_name} metrics={response.metrics} allocation={comparisonAllocation} latestAnalysis={latestAnalysis} latestAnalysisStatus={latestAnalysisStatus} latestAnalysisError={latestAnalysisError} onViewLatestAnalysis={onViewLatestAnalysis} immutable={immutable} /><div className={styles.resultGrid}><HistoricalTrajectories scenario={response.trajectory} latestAnalysis={latestAnalysis} /><Metadata requestedStart={response.scenario.requested_start_date} requestedEnd={response.scenario.requested_end_date} effectiveStart={metadata.effective_start_date} effectiveEnd={metadata.effective_end_date} priceCount={metadata.price_observation_count} returnCount={metadata.return_observation_count} /></div><Card className={styles.panel}><h3>{response.scenario.display_name}</h3><p>{response.scenario.description}</p></Card></section>;
  }
  if (result.type === 'allocation') {
    const response = result.response; const metadata = response.metadata;
    return <section className="simulation-results"><div className="simulation-results-heading"><div><span>SIMULATION RESULTS</span><h2>Allocation Change</h2><p>{response.portfolio_name} · Allocation Change{immutable ? ' · Immutable snapshot' : ''}</p></div><span className="results-status"><i /> Completed</span></div>{baseline && <Baseline baseline={baseline} />}<LatestAnalysisReference latestAnalysis={latestAnalysis} latestAnalysisStatus={latestAnalysisStatus} latestAnalysisError={latestAnalysisError} onViewLatestAnalysis={onViewLatestAnalysis} immutable={immutable} /><h3>Original allocation metrics</h3><Metrics metrics={response.original.metrics} /><h3>Modified allocation metrics</h3><Metrics metrics={response.modified.metrics} /><div className={styles.resultGrid}><Trajectories original={response.original.trajectory} modified={response.modified.trajectory} /><Metadata requestedStart={response.start_date} requestedEnd={response.end_date} effectiveStart={metadata.effective_start_date} effectiveEnd={metadata.effective_end_date} priceCount={metadata.price_observation_count} returnCount={metadata.return_observation_count} /></div><div className={styles.resultGrid}><Allocation title="Original Allocation" result={response.original} /><Allocation title="Modified Allocation" result={response.modified} /></div><SimulationComparison comparison={response.comparison} /></section>;
  }
  const response = result.response; const metadata = response.metadata;
  return <section className="simulation-results"><div className="simulation-results-heading"><div><span>SIMULATION RESULTS</span><h2>{response.scenario.display_name}</h2><p>{response.portfolio_name} · Combined Simulation{immutable ? ' · Immutable snapshot' : ''}</p></div><span className="results-status"><i /> Completed</span></div>{baseline && <Baseline baseline={baseline} />}<CombinedLatestAnalysisComparison metrics={response.modified.metrics} latestAnalysis={latestAnalysis} latestAnalysisStatus={latestAnalysisStatus} latestAnalysisError={latestAnalysisError} onViewLatestAnalysis={onViewLatestAnalysis} immutable={immutable} />{latestAnalysis && <CombinedLatestAnalysisTrajectories combined={response.modified.trajectory} latestAnalysis={latestAnalysis} />}<h3>Original allocation metrics</h3><Metrics metrics={response.original.metrics} /><h3>Modified allocation metrics</h3><Metrics metrics={response.modified.metrics} /><div className={styles.resultGrid}><Trajectories original={response.original.trajectory} modified={response.modified.trajectory} /><Metadata requestedStart={response.scenario.requested_start_date} requestedEnd={response.scenario.requested_end_date} effectiveStart={metadata.effective_start_date} effectiveEnd={metadata.effective_end_date} priceCount={metadata.price_observation_count} returnCount={metadata.return_observation_count} /></div><div className={styles.resultGrid}><Allocation title="Original Allocation" result={response.original} /><Allocation title="Modified Allocation" result={response.modified} /></div><SimulationComparison comparison={response.comparison} /><Card className={styles.panel}><h3>{response.scenario.display_name}</h3><p>{response.scenario.description}</p></Card></section>;
}
