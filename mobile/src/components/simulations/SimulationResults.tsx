import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import type { SimulationRunResult } from '../../simulation/SimulationProvider';
import {
  formatSimulationNumber,
  formatSimulationPercent,
  savedAnalysisTrajectory,
  simulationTypeLabel
} from '../../simulation/simulationFormatting';
import type {
  AllocationSimulationComparison,
  AllocationSimulationResult,
  HistoricalScenarioMetrics,
  SimulationBaselineValuationContext
} from '../../types/simulation';
import type { PlannedPortfolioBaselineContext, PortfolioAllocationInput } from '../../types/portfolio';
import type { PortfolioReportResponse } from '../../types/report';
import {
  formatCurrentAllocation,
  formatPortfolioMoney,
  formatPortfolioQuantity
} from '../../portfolio/portfolioFormatting';
import { colors, spacing } from '../../theme/theme';
import { SimulationTrajectoryChart } from '../charts/SimulationTrajectoryChart';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { formatReportTimestamp } from '../../report/reportFormatting';

function MetricGrid({ metrics }: { metrics: HistoricalScenarioMetrics }) {
  const values = [
    ['Starting value', formatSimulationNumber(metrics.normalized_starting_value)],
    ['Ending value', formatSimulationNumber(metrics.normalized_ending_value)],
    ['Cumulative return', formatSimulationPercent(metrics.cumulative_return)],
    ['Annualized volatility', formatSimulationPercent(metrics.annualized_volatility)],
    ['Sharpe ratio', formatSimulationNumber(metrics.sharpe_ratio)],
    ['Maximum drawdown', formatSimulationPercent(metrics.maximum_drawdown.max_drawdown)],
    ['Drawdown period', `${metrics.maximum_drawdown.peak_date ?? 'N/A'} → ${metrics.maximum_drawdown.trough_date ?? 'N/A'}`]
  ];
  return (
    <View style={styles.metrics}>
      {values.map(([label, value]) => (
        <View key={label} style={styles.metric}>
          <Text style={styles.metricLabel}>{label}</Text>
          <Text style={styles.metricValue}>{value}</Text>
        </View>
      ))}
    </View>
  );
}

function AllocationRows({ allocation }: { allocation: PortfolioAllocationInput[] }) {
  return (
    <View style={styles.allocationList}>
      {allocation.map((holding) => (
        <View key={holding.symbol} style={styles.allocationRow}>
          <Text style={styles.allocationSymbol}>{holding.symbol}</Text>
          <Text style={styles.allocationWeight}>{formatSimulationPercent(holding.weight)}</Text>
        </View>
      ))}
    </View>
  );
}

function AllocationList({ result }: { result: AllocationSimulationResult }) {
  return <AllocationRows allocation={result.allocation} />;
}

function allocationFromBaseline(
  baseline?: SimulationBaselineValuationContext | PlannedPortfolioBaselineContext
): PortfolioAllocationInput[] {
  if (!baseline) return [];
  if ('portfolio_type' in baseline) {
    return baseline.holdings.map((holding) => ({
      symbol: holding.symbol,
      weight: Number(holding.target_allocation)
    }));
  }
  return baseline.holdings.map((holding) => ({
    symbol: holding.symbol,
    weight: Number(holding.current_allocation)
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
  immutable
}: {
  scenarioName: string;
  metrics: HistoricalScenarioMetrics;
  allocation: PortfolioAllocationInput[];
  latestAnalysis?: PortfolioReportResponse | null;
  latestAnalysisStatus?: 'idle' | 'loading' | 'ready' | 'error';
  latestAnalysisError?: string | null;
  onViewLatestAnalysis?: () => void;
  immutable?: boolean;
}) {
  const reference = latestAnalysis?.analysis;
  const rows = [
    ['Cumulative return', reference ? formatSimulationPercent(reference.portfolio_metrics.cumulative_return) : 'Unavailable', formatSimulationPercent(metrics.cumulative_return)],
    ['Annualized volatility', reference ? formatSimulationPercent(reference.portfolio_metrics.annualized_volatility) : 'Unavailable', formatSimulationPercent(metrics.annualized_volatility)],
    ['Sharpe ratio', reference ? formatSimulationNumber(reference.portfolio_metrics.sharpe_ratio) : 'Unavailable', formatSimulationNumber(metrics.sharpe_ratio)],
    ['Maximum drawdown', reference ? formatSimulationPercent(reference.max_drawdown.max_drawdown) : 'Unavailable', formatSimulationPercent(metrics.maximum_drawdown.max_drawdown)]
  ];
  return (
    <Card style={styles.card}>
      <Text style={styles.cardTitle}>Latest portfolio analysis vs historical scenario</Text>
      <Text style={styles.body}>
        The reference uses the newest saved analysis for this portfolio. Both columns show backend-calculated metrics, but their historical periods may differ.
      </Text>
      <View style={styles.referenceContext}>
        {latestAnalysisStatus === 'loading' ? <Text style={styles.body}>Loading the latest saved portfolio analysis…</Text> : null}
        {latestAnalysisStatus === 'error' ? <Text style={styles.body}>{latestAnalysisError ?? 'Latest analysis details could not be loaded. The historical scenario result is still valid.'}</Text> : null}
        {latestAnalysisStatus === 'ready' && !latestAnalysis ? <Text style={styles.body}>No saved portfolio analysis exists yet, so Aura cannot show an original analysis reference.</Text> : null}
        {immutable && latestAnalysisStatus === undefined && !latestAnalysis ? <Text style={styles.body}>This immutable simulation snapshot does not contain a latest-analysis reference. Run a new historical scenario to compare against the portfolio's current latest saved analysis.</Text> : null}
        {latestAnalysis ? <>
          <Text style={styles.referenceLabel}>LATEST ANALYSIS SAVED</Text>
          <Text style={styles.referenceValue}>{formatReportTimestamp(latestAnalysis.created_at)}</Text>
          <Text style={styles.referenceLabel}>ANALYSIS PERIOD</Text>
          <Text style={styles.referenceValue}>{reference?.start_date} → {reference?.end_date}</Text>
          {onViewLatestAnalysis ? <Button title="View latest analysis details" variant="secondary" onPress={onViewLatestAnalysis} /> : null}
        </> : null}
      </View>
      <View style={styles.historicalMetrics}>
        <View style={[styles.historicalMetricRow, styles.historicalMetricHeader]}>
          <Text style={styles.historicalMetricLabel}>METRIC</Text>
          <Text style={styles.historicalMetricHeading}>LATEST ANALYSIS</Text>
          <Text style={styles.historicalMetricHeading} numberOfLines={2}>{scenarioName.toUpperCase()}</Text>
        </View>
        {rows.map(([label, original, scenario]) => (
          <View key={label} style={styles.historicalMetricRow}>
            <Text style={styles.historicalMetricLabel}>{label}</Text>
            <Text style={styles.historicalMetricValue}>{original}</Text>
            <Text style={[styles.historicalMetricValue, styles.historicalScenarioValue]}>{scenario}</Text>
          </View>
        ))}
      </View>
      <Text style={styles.baselineMeta}>The latest analysis is a saved reference, not a rerun over the scenario dates. Each chart path is normalized to 1.00 from its saved return observations.</Text>
      {allocation.length ? (
        <>
          <Text style={styles.allocationHeading}>Allocation used by this scenario run</Text>
          <AllocationRows allocation={allocation} />
        </>
      ) : null}
    </Card>
  );
}

function LatestAnalysisReference({
  latestAnalysis,
  latestAnalysisStatus,
  latestAnalysisError,
  onViewLatestAnalysis,
  immutable
}: {
  latestAnalysis?: PortfolioReportResponse | null;
  latestAnalysisStatus?: 'idle' | 'loading' | 'ready' | 'error';
  latestAnalysisError?: string | null;
  onViewLatestAnalysis?: () => void;
  immutable?: boolean;
}) {
  const analysis = latestAnalysis?.analysis;
  const metrics = analysis ? [
    ['Cumulative return', formatSimulationPercent(analysis.portfolio_metrics.cumulative_return)],
    ['Annualized volatility', formatSimulationPercent(analysis.portfolio_metrics.annualized_volatility)],
    ['Sharpe ratio', formatSimulationNumber(analysis.portfolio_metrics.sharpe_ratio)],
    ['Maximum drawdown', formatSimulationPercent(analysis.max_drawdown.max_drawdown)]
  ] : [];
  return (
    <Card style={styles.card}>
      <Text style={styles.cardTitle}>Latest saved portfolio analysis</Text>
      <Text style={styles.body}>This is additional saved context. The allocation comparison below still uses Aura's backend original and modified results over the same requested period.</Text>
      <View style={styles.referenceContext}>
        {latestAnalysisStatus === 'loading' ? <Text style={styles.body}>Loading the latest saved portfolio analysis…</Text> : null}
        {latestAnalysisStatus === 'error' ? <Text style={styles.body}>{latestAnalysisError ?? 'Latest analysis details could not be loaded. The allocation comparison is still valid.'}</Text> : null}
        {latestAnalysisStatus === 'ready' && !latestAnalysis ? <Text style={styles.body}>No saved portfolio analysis exists yet. Run an analysis to create this additional reference.</Text> : null}
        {immutable && latestAnalysisStatus === undefined && !latestAnalysis ? <Text style={styles.body}>This immutable simulation snapshot does not contain a latest-analysis reference. Run a new simulation comparison to use the portfolio's current latest saved analysis.</Text> : null}
        {latestAnalysis ? <>
          <Text style={styles.referenceLabel}>LATEST ANALYSIS SAVED</Text>
          <Text style={styles.referenceValue}>{formatReportTimestamp(latestAnalysis.created_at)}</Text>
          <Text style={styles.referenceLabel}>ANALYSIS PERIOD</Text>
          <Text style={styles.referenceValue}>{analysis?.start_date} → {analysis?.end_date}</Text>
          {onViewLatestAnalysis ? <Button title="View latest analysis details" variant="secondary" onPress={onViewLatestAnalysis} /> : null}
        </> : null}
      </View>
      {metrics.length ? <View style={styles.referenceMetrics}>
        {metrics.map(([label, value]) => <View key={label} style={styles.referenceMetric}>
          <Text style={styles.referenceLabel}>{label.toUpperCase()}</Text>
          <Text style={styles.referenceMetricValue}>{value}</Text>
        </View>)}
      </View> : null}
    </Card>
  );
}

function CombinedLatestAnalysisComparison({
  metrics,
  latestAnalysis,
  latestAnalysisStatus,
  latestAnalysisError,
  onViewLatestAnalysis,
  immutable
}: {
  metrics: HistoricalScenarioMetrics;
  latestAnalysis?: PortfolioReportResponse | null;
  latestAnalysisStatus?: 'idle' | 'loading' | 'ready' | 'error';
  latestAnalysisError?: string | null;
  onViewLatestAnalysis?: () => void;
  immutable?: boolean;
}) {
  const reference = latestAnalysis?.analysis;
  const rows = [
    ['Cumulative return', reference ? formatSimulationPercent(reference.portfolio_metrics.cumulative_return) : 'Unavailable', formatSimulationPercent(metrics.cumulative_return)],
    ['Annualized volatility', reference ? formatSimulationPercent(reference.portfolio_metrics.annualized_volatility) : 'Unavailable', formatSimulationPercent(metrics.annualized_volatility)],
    ['Sharpe ratio', reference ? formatSimulationNumber(reference.portfolio_metrics.sharpe_ratio) : 'Unavailable', formatSimulationNumber(metrics.sharpe_ratio)],
    ['Maximum drawdown', reference ? formatSimulationPercent(reference.max_drawdown.max_drawdown) : 'Unavailable', formatSimulationPercent(metrics.maximum_drawdown.max_drawdown)]
  ];
  return (
    <Card style={styles.card}>
      <Text style={styles.cardTitle}>Latest portfolio analysis vs new combined simulation</Text>
      <Text style={styles.body}>
        The new combined result is the modified allocation under the selected historical scenario. Both columns are backend-calculated, but their historical periods may differ.
      </Text>
      <View style={styles.referenceContext}>
        {latestAnalysisStatus === 'loading' ? <Text style={styles.body}>Loading the latest saved portfolio analysis…</Text> : null}
        {latestAnalysisStatus === 'error' ? <Text style={styles.body}>{latestAnalysisError ?? 'Latest analysis details could not be loaded. The combined simulation result is still valid.'}</Text> : null}
        {latestAnalysisStatus === 'ready' && !latestAnalysis ? <Text style={styles.body}>No saved portfolio analysis exists yet, so Aura cannot show the requested comparison.</Text> : null}
        {immutable && latestAnalysisStatus === undefined && !latestAnalysis ? <Text style={styles.body}>This immutable simulation snapshot does not contain a latest-analysis reference. Run a new combined simulation to compare against the portfolio's current latest saved analysis.</Text> : null}
        {latestAnalysis ? <>
          <Text style={styles.referenceLabel}>LATEST ANALYSIS SAVED</Text>
          <Text style={styles.referenceValue}>{formatReportTimestamp(latestAnalysis.created_at)}</Text>
          <Text style={styles.referenceLabel}>ANALYSIS PERIOD</Text>
          <Text style={styles.referenceValue}>{reference?.start_date} → {reference?.end_date}</Text>
          {onViewLatestAnalysis ? <Button title="View latest analysis details" variant="secondary" onPress={onViewLatestAnalysis} /> : null}
        </> : null}
      </View>
      <View style={styles.historicalMetrics}>
        <View style={[styles.historicalMetricRow, styles.historicalMetricHeader]}>
          <Text style={styles.historicalMetricLabel}>METRIC</Text>
          <Text style={styles.historicalMetricHeading}>LATEST ANALYSIS</Text>
          <Text style={styles.historicalMetricHeading} numberOfLines={2}>NEW COMBINED RESULT</Text>
        </View>
        {rows.map(([label, original, combined]) => (
          <View key={label} style={styles.historicalMetricRow}>
            <Text style={styles.historicalMetricLabel}>{label}</Text>
            <Text style={styles.historicalMetricValue}>{original}</Text>
            <Text style={[styles.historicalMetricValue, styles.historicalScenarioValue]}>{combined}</Text>
          </View>
        ))}
      </View>
      <Text style={styles.baselineMeta}>The latest analysis remains a saved reference; it is not recalculated over the combined scenario dates.</Text>
    </Card>
  );
}

function Comparison({ comparison }: { comparison: AllocationSimulationComparison }) {
  const values = [
    ['Ending value delta', formatSimulationNumber(comparison.normalized_ending_value_delta)],
    ['Return delta', formatSimulationPercent(comparison.cumulative_return_delta)],
    ['Volatility delta', formatSimulationPercent(comparison.annualized_volatility_delta)],
    ['Sharpe delta', formatSimulationNumber(comparison.sharpe_ratio_delta)],
    ['Drawdown delta', formatSimulationPercent(comparison.maximum_drawdown_delta)]
  ];
  return (
    <Card style={styles.card}>
      <Text style={styles.cardTitle}>Comparison</Text>
      {values.map(([label, value]) => (
        <View key={label} style={styles.comparisonRow}>
          <Text style={styles.comparisonLabel}>{label}</Text>
          <Text style={styles.comparisonValue}>{value}</Text>
        </View>
      ))}
    </Card>
  );
}

export function SimulationResults({
  result,
  baseline,
  originalAllocation,
  latestAnalysis,
  latestAnalysisStatus,
  latestAnalysisError,
  onViewLatestAnalysis,
  immutable = false
}: {
  result: SimulationRunResult;
  baseline?: SimulationBaselineValuationContext | PlannedPortfolioBaselineContext;
  originalAllocation?: PortfolioAllocationInput[];
  latestAnalysis?: PortfolioReportResponse | null;
  latestAnalysisStatus?: 'idle' | 'loading' | 'ready' | 'error';
  latestAnalysisError?: string | null;
  onViewLatestAnalysis?: () => void;
  immutable?: boolean;
}) {
  const baselineCard = baseline ? <BaselineCard baseline={baseline} /> : null;
  if (result.type === 'historical-scenario') {
    const response = result.response;
    const comparisonAllocation = originalAllocation ?? allocationFromBaseline(baseline);
    return (
      <View style={styles.wrapper}>
        <Text style={styles.eyebrow}>RESULT · HISTORICAL SCENARIO</Text>
        <Text style={styles.title}>{response.portfolio_name}</Text>
        <Text style={styles.subtitle}>{response.scenario.display_name} · {response.scenario.description}</Text>
        {baselineCard}
        <HistoricalComparison
          scenarioName={response.scenario.display_name}
          metrics={response.metrics}
          allocation={comparisonAllocation}
          latestAnalysis={latestAnalysis}
          latestAnalysisStatus={latestAnalysisStatus}
          latestAnalysisError={latestAnalysisError}
          onViewLatestAnalysis={onViewLatestAnalysis}
          immutable={immutable}
        />
        <MetadataCard requested={`${response.scenario.requested_start_date} → ${response.scenario.requested_end_date}`} metadata={response.metadata} />
        <Card style={styles.card}>
          <Text style={styles.cardTitle}>Latest analysis vs historical scenario</Text>
          <Text style={styles.body}>Select one line for its own date and value labels. All lines share only the normalized-value labels because the periods can differ.</Text>
          <SimulationTrajectoryChart series={[
            ...(latestAnalysis ? [{
              label: 'Latest analysis',
              color: colors.muted as string,
              points: savedAnalysisTrajectory(latestAnalysis.analysis)
            }] : []),
            { label: 'Historical scenario', color: colors.primary as string, points: response.trajectory }
          ]} />
        </Card>
      </View>
    );
  }

  const requested = result.type === 'allocation'
    ? `${result.response.start_date} → ${result.response.end_date}`
    : `${result.response.scenario.requested_start_date} → ${result.response.scenario.requested_end_date}`;
  const scenario = result.type === 'combined' ? result.response.scenario : null;
  const response = result.response;

  return (
    <View style={styles.wrapper}>
      <Text style={styles.eyebrow}>RESULT · {simulationTypeLabel(result.type).toUpperCase()}</Text>
      <Text style={styles.title}>{response.portfolio_name}</Text>
      {scenario ? <Text style={styles.subtitle}>{scenario.display_name} · {scenario.description}</Text> : null}
      {baselineCard}
      {result.type === 'allocation' ? <LatestAnalysisReference
        latestAnalysis={latestAnalysis}
        latestAnalysisStatus={latestAnalysisStatus}
        latestAnalysisError={latestAnalysisError}
        onViewLatestAnalysis={onViewLatestAnalysis}
        immutable={immutable}
      /> : null}
      {result.type === 'combined' ? <CombinedLatestAnalysisComparison
        metrics={response.modified.metrics}
        latestAnalysis={latestAnalysis}
        latestAnalysisStatus={latestAnalysisStatus}
        latestAnalysisError={latestAnalysisError}
        onViewLatestAnalysis={onViewLatestAnalysis}
        immutable={immutable}
      /> : null}
      {result.type === 'combined' && latestAnalysis ? <Card style={styles.card}>
        <Text style={styles.cardTitle}>Latest analysis vs new combined simulation</Text>
        <Text style={styles.body}>Select one line for its own date and value labels. All lines share only normalized-value labels because the saved periods may differ.</Text>
        <SimulationTrajectoryChart series={[
          {
            label: 'Latest analysis',
            color: colors.muted as string,
            points: savedAnalysisTrajectory(latestAnalysis.analysis)
          },
          {
            label: 'New combined result',
            color: colors.primary as string,
            points: response.modified.trajectory
          }
        ]} />
      </Card> : null}
      <MetadataCard requested={requested} metadata={response.metadata} />
      <Card style={styles.card}>
        <Text style={styles.cardTitle}>Original allocation and metrics</Text>
        <AllocationList result={response.original} />
        <MetricGrid metrics={response.original.metrics} />
      </Card>
      <Card style={styles.card}>
        <Text style={styles.cardTitle}>Modified allocation and metrics</Text>
        <AllocationList result={response.modified} />
        <MetricGrid metrics={response.modified.metrics} />
      </Card>
      <Card style={styles.card}>
        <Text style={styles.cardTitle}>Normalized trajectories</Text>
        <SimulationTrajectoryChart series={[
          { label: 'Original', color: colors.muted as string, points: response.original.trajectory },
          { label: 'Modified', color: colors.primary as string, points: response.modified.trajectory }
        ]} />
      </Card>
      <Comparison comparison={response.comparison} />
    </View>
  );
}

function BaselineCard({ baseline }: {
  baseline: SimulationBaselineValuationContext | PlannedPortfolioBaselineContext;
}) {
  if ('portfolio_type' in baseline) {
    return (
      <Card style={styles.plannedBaselineCard}>
        <Text style={styles.cardTitle}>Saved planned allocation</Text>
        <Text style={styles.baselineValue}>
          {formatPortfolioMoney(baseline.total_proposed_amount, baseline.plan_currency)}
        </Text>
        <Text style={styles.baselineMeta}>{baseline.hypothetical_notice}</Text>
        {baseline.holdings.map((holding) => (
          <View key={holding.id} style={styles.baselineRow}>
            <View style={{ flex: 1 }}>
              <Text style={styles.allocationSymbol}>{holding.symbol}</Text>
              <Text style={styles.baselineMeta}>
                Proposed {formatPortfolioMoney(holding.proposed_amount, baseline.plan_currency)}
              </Text>
            </View>
            <Text style={styles.allocationWeight}>
              {formatSimulationPercent(Number(holding.target_allocation))}
            </Text>
          </View>
        ))}
        <Text style={styles.baselineMeta}>
          Estimated shares are for display only and do not affect this simulation.
        </Text>
      </Card>
    );
  }
  return (
    <Card style={styles.baselineCard}>
      <Text style={styles.cardTitle}>Saved current holdings</Text>
      <Text style={styles.baselineValue}>
        {formatPortfolioMoney(baseline.total_current_value_usd, 'USD')}
      </Text>
      <Text style={styles.baselineMeta}>
        Valued {baseline.valuation_date} · prices {baseline.oldest_price_as_of} to {baseline.newest_price_as_of}
      </Text>
      {baseline.holdings.map((holding) => (
        <View key={`${holding.position}-${holding.symbol}`} style={styles.baselineRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.allocationSymbol}>{holding.symbol}</Text>
            <Text style={styles.baselineMeta}>
              {formatPortfolioQuantity(holding.shares)} shares · price {formatPortfolioMoney(holding.asset_price, 'USD')}
            </Text>
          </View>
          <View style={styles.baselineRight}>
            <Text style={styles.allocationWeight}>{formatPortfolioMoney(holding.current_value_usd, 'USD')}</Text>
            <Text style={styles.baselineMeta}>{formatCurrentAllocation(holding.current_allocation)}</Text>
          </View>
        </View>
      ))}
      <Text style={styles.baselineMeta}>These saved values are not updated with later market prices.</Text>
    </Card>
  );
}

function MetadataCard({ requested, metadata }: {
  requested: string;
  metadata: {
    effective_start_date: string;
    effective_end_date: string;
    price_observation_count: number;
    return_observation_count: number;
  };
}) {
  return (
    <Card style={styles.card}>
      <Text style={styles.cardTitle}>Requested period</Text>
      <Text style={styles.body}>{requested}</Text>
      <Text style={styles.cardTitle}>Historical data period</Text>
      <Text style={styles.body}>{metadata.effective_start_date} → {metadata.effective_end_date}</Text>
      <Text style={styles.observations}>{metadata.price_observation_count} prices · {metadata.return_observation_count} returns</Text>
    </Card>
  );
}

const styles = StyleSheet.create({
  wrapper: { gap: spacing.md, marginTop: spacing.xxl },
  eyebrow: { color: colors.primary, fontSize: 10, fontWeight: '900', letterSpacing: 1.1 },
  title: { color: colors.text, fontSize: 22, fontWeight: '900' },
  subtitle: { color: colors.textSecondary, fontSize: 12, lineHeight: 18 },
  card: { gap: spacing.md },
  cardTitle: { color: colors.text, fontSize: 14, fontWeight: '900' },
  body: { color: colors.textSecondary, fontSize: 12 },
  observations: { color: colors.muted, fontSize: 10 },
  metrics: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  metric: { flexGrow: 1, flexBasis: 132, backgroundColor: colors.surfaceAlt, borderRadius: 12, padding: spacing.md },
  metricLabel: { color: colors.muted, fontSize: 9, fontWeight: '800' },
  metricValue: { color: colors.text, fontSize: 12, fontWeight: '900', marginTop: spacing.xs },
  allocationList: { gap: spacing.sm },
  allocationRow: { flexDirection: 'row', justifyContent: 'space-between' },
  allocationSymbol: { color: colors.textSecondary, fontWeight: '800' },
  allocationWeight: { color: colors.text, fontWeight: '900' },
  comparisonRow: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', gap: spacing.md },
  comparisonLabel: { color: colors.textSecondary, fontSize: 12, flexGrow: 1, flexBasis: 120 },
  comparisonValue: { color: colors.text, fontSize: 12, fontWeight: '900', flexShrink: 1, textAlign: 'right' },
  historicalMetrics: { borderWidth: 1, borderColor: colors.border, borderRadius: 12, overflow: 'hidden' },
  historicalMetricRow: { minHeight: 44, flexDirection: 'row', alignItems: 'center', borderTopWidth: 1, borderTopColor: colors.border, paddingHorizontal: spacing.sm, gap: spacing.sm },
  historicalMetricHeader: { borderTopWidth: 0, backgroundColor: colors.summaryBackground },
  historicalMetricLabel: { flex: 1.25, color: colors.muted, fontSize: 9, fontWeight: '800' },
  historicalMetricHeading: { flex: 1, color: colors.textSecondary, fontSize: 9, fontWeight: '900', textAlign: 'right' },
  historicalMetricValue: { flex: 1, color: colors.text, fontSize: 11, fontWeight: '900', textAlign: 'right' },
  historicalScenarioValue: { color: colors.primary },
  allocationHeading: { color: colors.text, fontSize: 11, fontWeight: '900', marginTop: spacing.xs },
  baselineCard: { gap: spacing.md, backgroundColor: colors.cyanBackground },
  plannedBaselineCard: { gap: spacing.md, backgroundColor: colors.summaryBackground, borderColor: colors.primary },
  baselineValue: { color: colors.text, fontSize: 23, fontWeight: '900' },
  baselineMeta: { color: colors.textSecondary, fontSize: 10, lineHeight: 15 },
  baselineRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md, alignItems: 'center' },
  baselineRight: { alignItems: 'flex-end' },
  referenceContext: { gap: spacing.xs, padding: spacing.md, borderWidth: 1, borderColor: colors.border, borderRadius: 12, backgroundColor: colors.cyanBackground },
  referenceLabel: { color: colors.muted, fontSize: 9, fontWeight: '900', marginTop: spacing.xs },
  referenceValue: { color: colors.text, fontSize: 11, fontWeight: '800', marginBottom: spacing.xs },
  referenceMetrics: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  referenceMetric: { flexGrow: 1, flexBasis: 132, padding: spacing.md, borderWidth: 1, borderColor: colors.border, borderRadius: 12, backgroundColor: colors.surfaceAlt },
  referenceMetricValue: { color: colors.text, fontSize: 13, fontWeight: '900', marginTop: spacing.xs }
});
