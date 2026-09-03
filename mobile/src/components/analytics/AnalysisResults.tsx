import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import type { PortfolioAnalysisResponse } from '../../types/analytics';
import { colors, spacing } from '../../theme/theme';
import {
  formatAnalysisNumber,
  formatRatioPercent,
  riskTone
} from '../../report/reportFormatting';
import { AssetRelationshipBars } from '../charts/AssetRelationshipBars';
import { PortfolioReturnsChart } from '../charts/PortfolioReturnsChart';
import { Card } from '../ui/Card';
import { RiskBadge } from '../ui/RiskBadge';
import { SectionHeader } from '../ui/SectionHeader';
import { Tag } from '../ui/Tag';
import { WebKpiCard } from '../ui/WebKpiCard';

export function AnalysisResults({
  analysis
}: {
  analysis: PortfolioAnalysisResponse;
}) {
  const metrics = analysis.portfolio_metrics;
  const drawdown = analysis.max_drawdown;
  const diversification = analysis.diversification;
  const concentration = analysis.concentration;
  const risk = analysis.risk_classification;

  return (
    <View style={styles.results}>
      <Card style={styles.summaryCard}>
        <View style={styles.summaryHeading}>
          <View style={{ flex: 1 }}>
            <Text style={styles.overline}>BACKEND ANALYSIS</Text>
            <Text style={styles.summaryTitle}>{analysis.portfolio_name}</Text>
          </View>
          <RiskBadge level={risk.risk_level} />
        </View>
        <Text style={styles.summaryText}>
          Risk score {risk.risk_score.toFixed(1)}/100 · {diversification.level} diversification
        </Text>
        {risk.reasons.map((reason, index) => (
          <Text key={`${index}-${reason}`} style={styles.reason}>• {reason}</Text>
        ))}
      </Card>

      <View style={styles.metricGrid}>
        <WebKpiCard
          icon="speedometer-outline"
          label="Risk Score"
          value={`${risk.risk_score.toFixed(1)}/100`}
          meta={risk.risk_level}
          tone={riskTone(risk.risk_level)}
        />
        <WebKpiCard
          icon="trending-up-outline"
          label="Cumulative Return"
          value={formatRatioPercent(metrics.cumulative_return)}
          meta="Saved period"
          tone={metrics.cumulative_return < 0 ? 'danger' : 'success'}
        />
        <WebKpiCard
          icon="analytics-outline"
          label="Annualized Return"
          value={formatRatioPercent(metrics.annualized_return)}
          meta="Backend result"
          tone={metrics.annualized_return < 0 ? 'danger' : 'success'}
        />
        <WebKpiCard
          icon="pulse-outline"
          label="Volatility"
          value={formatRatioPercent(metrics.annualized_volatility)}
          meta="Annualized"
          tone="warning"
        />
        <WebKpiCard
          icon="stats-chart-outline"
          label="Sharpe Ratio"
          value={formatAnalysisNumber(metrics.sharpe_ratio)}
          meta="Risk-adjusted"
          tone="blue"
        />
        <WebKpiCard
          icon="trending-down-outline"
          label="Max Drawdown"
          value={formatRatioPercent(drawdown.max_drawdown)}
          meta={`${drawdown.peak_date ?? 'N/A'} → ${drawdown.trough_date ?? 'N/A'}`}
          tone="danger"
        />
      </View>

      <SectionHeader title="Portfolio Return Series" />
      <Card style={styles.sectionCard}>
        <Text style={styles.cardText}>
          Ordered periodic returns supplied by the backend. No benchmark or cumulative series is generated on-device.
        </Text>
        <PortfolioReturnsChart points={analysis.portfolio_returns} />
        <Text style={styles.observationCount}>
          {analysis.portfolio_returns.length} return observations
        </Text>
      </Card>

      <SectionHeader title="Risk Drivers" />
      <View style={styles.list}>
        {analysis.risk_drivers.entries.map((driver) => (
          <Card key={`${driver.rank}-${driver.symbol}`} style={styles.driverCard}>
            <View style={styles.rowBetween}>
              <Text style={styles.driverTitle}>#{driver.rank} {driver.symbol}</Text>
              {driver.symbol === analysis.risk_drivers.top_driver ? (
                <Tag label="Top driver" tone="danger" />
              ) : null}
            </View>
            <View style={styles.dataGrid}>
              <Metric label="Weight" value={formatRatioPercent(driver.weight)} />
              <Metric
                label="Asset volatility"
                value={formatRatioPercent(driver.annualized_asset_volatility)}
              />
              <Metric
                label="Marginal contribution"
                value={formatRatioPercent(driver.marginal_volatility_contribution)}
              />
              <Metric
                label="Component contribution"
                value={formatRatioPercent(driver.component_volatility_contribution)}
              />
              <Metric
                label="Contribution share"
                value={formatRatioPercent(driver.percentage_volatility_contribution)}
              />
            </View>
          </Card>
        ))}
      </View>

      <SectionHeader title="Individual Asset Metrics" />
      <View style={styles.list}>
        {analysis.asset_metrics.map((asset) => (
          <Card key={asset.symbol} style={styles.sectionCard}>
            <View style={styles.rowBetween}>
              <Text style={styles.assetSymbol}>{asset.symbol}</Text>
              <Tag label={formatRatioPercent(asset.weight)} tone="primary" />
            </View>
            <View style={styles.dataGrid}>
              <Metric label="Cumulative return" value={formatRatioPercent(asset.cumulative_return)} />
              <Metric label="Annualized return" value={formatRatioPercent(asset.annualized_return)} />
              <Metric label="Volatility" value={formatRatioPercent(asset.annualized_volatility)} />
              <Metric label="Max drawdown" value={formatRatioPercent(asset.max_drawdown)} />
              <Metric label="Sharpe ratio" value={formatAnalysisNumber(asset.sharpe_ratio)} />
            </View>
          </Card>
        ))}
      </View>

      <SectionHeader title="Asset Relationships" />
      <Card style={styles.sectionCard}>
        <AssetRelationshipBars pairs={analysis.correlation_pairs} />
      </Card>

      <SectionHeader title="Diversification and Concentration" />
      <Card style={styles.sectionCard}>
        <View style={styles.rowBetween}>
          <Text style={styles.cardTitle}>{diversification.level} diversification</Text>
          <Text style={styles.scoreValue}>
            {formatAnalysisNumber(diversification.overall_score, 1)}
          </Text>
        </View>
        <View style={styles.dataGrid}>
          <Metric label="Weight score" value={formatAnalysisNumber(diversification.weight_score, 1)} />
          <Metric label="Correlation score" value={formatAnalysisNumber(diversification.correlation_score, 1)} />
          <Metric label="Average correlation" value={formatAnalysisNumber(diversification.average_pairwise_correlation, 3)} />
          <Metric label="Defined pairs" value={`${diversification.defined_pair_count}/${diversification.total_pair_count}`} />
          <Metric label="Largest weight" value={formatRatioPercent(concentration.largest_weight)} />
          <Metric label={`Top ${concentration.top_n} weight`} value={formatRatioPercent(concentration.top_n_weight)} />
          <Metric label="Effective assets" value={formatAnalysisNumber(concentration.effective_number_of_assets)} />
          <Metric label="HHI" value={formatAnalysisNumber(concentration.hhi, 4)} />
        </View>
      </Card>

      <SectionHeader title="Analysis Metadata" />
      <Card style={styles.sectionCard}>
        <Metadata label="Requested period" value={`${analysis.start_date} → ${analysis.end_date}`} />
        <Metadata label="Observed period" value={`${analysis.metadata.analysis_start} → ${analysis.metadata.analysis_end}`} />
        <Metadata label="Price observations" value={String(analysis.metadata.price_observation_count)} />
        <Metadata label="Return observations" value={String(analysis.metadata.return_observation_count)} />
        <Metadata label="Assets analyzed" value={String(analysis.metadata.asset_count)} />
      </Card>

      <Text style={styles.education}>
        Historical analytics are educational, not investment recommendations. Every financial metric above comes from Aura's backend report.
      </Text>
    </View>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.metricItem}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>{value}</Text>
    </View>
  );
}

function Metadata({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.metadataRow}>
      <Text style={styles.metadataLabel}>{label}</Text>
      <Text style={styles.metadataValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  results: { gap: spacing.md, marginTop: spacing.xl },
  summaryCard: { gap: spacing.sm, backgroundColor: colors.summaryBackground },
  summaryHeading: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  overline: { color: colors.primary, fontSize: 9, fontWeight: '900', letterSpacing: 1 },
  summaryTitle: { color: colors.text, fontSize: 19, fontWeight: '900', marginTop: 4 },
  summaryText: { color: colors.textSecondary, fontSize: 12, lineHeight: 18 },
  reason: { color: colors.textSecondary, fontSize: 11, lineHeight: 17 },
  metricGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    gap: spacing.md
  },
  list: { gap: spacing.md },
  sectionCard: { gap: spacing.md },
  cardTitle: { color: colors.text, fontSize: 15, fontWeight: '900', flex: 1 },
  cardText: { color: colors.textSecondary, fontSize: 11, lineHeight: 17 },
  observationCount: { color: colors.muted, fontSize: 10, textAlign: 'center' },
  rowBetween: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: spacing.md
  },
  driverCard: { gap: spacing.md },
  driverTitle: { color: colors.text, fontSize: 16, fontWeight: '900' },
  assetSymbol: { color: colors.primary, fontSize: 18, fontWeight: '900' },
  scoreValue: { color: colors.primary, fontSize: 22, fontWeight: '900' },
  dataGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  metricItem: { width: '47%', gap: 3 },
  metricLabel: { color: colors.muted, fontSize: 9, lineHeight: 13 },
  metricValue: { color: colors.text, fontSize: 12, fontWeight: '900' },
  metadataRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: spacing.md,
    paddingVertical: spacing.xs
  },
  metadataLabel: { color: colors.muted, fontSize: 10, flex: 1 },
  metadataValue: { color: colors.text, fontSize: 10, fontWeight: '800', textAlign: 'right', flex: 1.5 },
  education: {
    color: colors.muted,
    fontSize: 10,
    lineHeight: 16,
    textAlign: 'center',
    marginTop: spacing.md
  }
});
