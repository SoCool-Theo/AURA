import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import type { SimulationRunResult } from '../../simulation/SimulationProvider';
import {
  formatSimulationNumber,
  formatSimulationPercent,
  simulationTypeLabel
} from '../../simulation/simulationFormatting';
import type {
  AllocationSimulationComparison,
  AllocationSimulationResult,
  HistoricalScenarioMetrics,
  SimulationBaselineValuationContext
} from '../../types/simulation';
import {
  formatCurrentAllocation,
  formatPortfolioMoney,
  formatPortfolioQuantity
} from '../../portfolio/portfolioFormatting';
import { colors, spacing } from '../../theme/theme';
import { SimulationTrajectoryChart } from '../charts/SimulationTrajectoryChart';
import { Card } from '../ui/Card';

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

function AllocationList({ result }: { result: AllocationSimulationResult }) {
  return (
    <View style={styles.allocationList}>
      {result.allocation.map((holding) => (
        <View key={holding.symbol} style={styles.allocationRow}>
          <Text style={styles.allocationSymbol}>{holding.symbol}</Text>
          <Text style={styles.allocationWeight}>{formatSimulationPercent(holding.weight)}</Text>
        </View>
      ))}
    </View>
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
      <Text style={styles.cardTitle}>Backend comparison</Text>
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
  baseline
}: {
  result: SimulationRunResult;
  baseline?: SimulationBaselineValuationContext;
}) {
  const baselineCard = baseline ? <BaselineCard baseline={baseline} /> : null;
  if (result.type === 'historical-scenario') {
    const response = result.response;
    return (
      <View style={styles.wrapper}>
        <Text style={styles.eyebrow}>RESULT · HISTORICAL SCENARIO</Text>
        <Text style={styles.title}>{response.portfolio_name}</Text>
        <Text style={styles.subtitle}>{response.scenario.display_name} · {response.scenario.description}</Text>
        {baselineCard}
        <MetadataCard requested={`${response.scenario.requested_start_date} → ${response.scenario.requested_end_date}`} metadata={response.metadata} />
        <Card style={styles.card}>
          <Text style={styles.cardTitle}>Portfolio metrics</Text>
          <MetricGrid metrics={response.metrics} />
        </Card>
        <Card style={styles.card}>
          <Text style={styles.cardTitle}>Normalized trajectory</Text>
          <SimulationTrajectoryChart series={[{ label: 'Portfolio', color: colors.primary as string, points: response.trajectory }]} />
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

function BaselineCard({ baseline }: { baseline: SimulationBaselineValuationContext }) {
  return (
    <Card style={styles.baselineCard}>
      <Text style={styles.cardTitle}>Frozen real-holding baseline</Text>
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
      <Text style={styles.baselineMeta}>This saved baseline is immutable and is not revalued on this screen.</Text>
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
      <Text style={styles.cardTitle}>Effective backend period</Text>
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
  metric: { width: '48%', backgroundColor: colors.surfaceAlt, borderRadius: 12, padding: spacing.md },
  metricLabel: { color: colors.muted, fontSize: 9, fontWeight: '800' },
  metricValue: { color: colors.text, fontSize: 12, fontWeight: '900', marginTop: spacing.xs },
  allocationList: { gap: spacing.sm },
  allocationRow: { flexDirection: 'row', justifyContent: 'space-between' },
  allocationSymbol: { color: colors.textSecondary, fontWeight: '800' },
  allocationWeight: { color: colors.text, fontWeight: '900' },
  comparisonRow: { flexDirection: 'row', justifyContent: 'space-between', gap: spacing.md },
  comparisonLabel: { color: colors.textSecondary, fontSize: 12 },
  comparisonValue: { color: colors.text, fontSize: 12, fontWeight: '900' },
  baselineCard: { gap: spacing.md, backgroundColor: colors.cyanBackground },
  baselineValue: { color: colors.text, fontSize: 23, fontWeight: '900' },
  baselineMeta: { color: colors.textSecondary, fontSize: 10, lineHeight: 15 },
  baselineRow: { flexDirection: 'row', gap: spacing.md, alignItems: 'center' },
  baselineRight: { alignItems: 'flex-end' }
});
