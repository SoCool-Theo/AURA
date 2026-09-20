import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import {
  formatCurrentAllocation,
  formatPortfolioMoney,
  formatPortfolioQuantity
} from '../../portfolio/portfolioFormatting';
import {
  reportMetricAmountContent,
  reportMonetaryMetrics,
  type ReportMonetaryMetricKey
} from '../../report/reportMetricDetails';
import {
  isPortfolioReportV2,
  isPortfolioReportV3,
  type PortfolioReportResponse
} from '../../types/report';
import { colors, spacing } from '../../theme/theme';
import {
  filterReturnPoints,
  RETURN_VIEW_RANGES,
  type ReturnViewRange
} from '../../dashboard/dashboardPresentation';
import {
  formatAnalysisNumber,
  formatRatioPercent,
  riskTone
} from '../../report/reportFormatting';
import { AssetRelationshipBars } from '../charts/AssetRelationshipBars';
import { PortfolioReturnsChart } from '../charts/PortfolioReturnsChart';
import {
  MetricAmountSheet
} from './MetricAmountSheet';
import { Card } from '../ui/Card';
import { RiskBadge } from '../ui/RiskBadge';
import { SectionHeader } from '../ui/SectionHeader';
import { Tag } from '../ui/Tag';
import { WebKpiCard } from '../ui/WebKpiCard';

export function AnalysisResults({
  report,
  onOpenAsset
}: {
  report: PortfolioReportResponse;
  onOpenAsset?: (symbol: string) => void;
}) {
  const analysis = report.analysis;
  const reportV2 = isPortfolioReportV2(report) ? report : null;
  const reportV3 = isPortfolioReportV3(report) ? report : null;
  const monetary = reportMonetaryMetrics(report);
  const [selectedMetric, setSelectedMetric] = useState<ReportMonetaryMetricKey | null>(null);
  const [returnViewRange, setReturnViewRange] = useState<ReturnViewRange>('1Y');
  const metrics = analysis.portfolio_metrics;
  const drawdown = analysis.max_drawdown;
  const diversification = analysis.diversification;
  const concentration = analysis.concentration;
  const historicalValue = reportV2 ? analysis.historical_value_context : null;
  const portfolioReturnLabel = reportV2
    ? 'Historical Portfolio Return'
    : 'Cumulative Return';
  const risk = analysis.risk_classification;
  const visibleReturns = filterReturnPoints(analysis.portfolio_returns, returnViewRange);

  return (
    <View style={styles.results}>
      <Card style={styles.summaryCard}>
        <View style={styles.summaryHeading}>
          <View style={{ flex: 1 }}>
            <Text style={styles.overline}>RISK ANALYSIS</Text>
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

      {reportV3 ? (
        <Card style={styles.plannedCard}>
          <View style={styles.rowBetween}>
            <View style={{ flex: 1 }}>
              <Text style={styles.overline}>SAVED PLANNED ALLOCATION</Text>
              <Text style={styles.snapshotValue}>
                {formatPortfolioMoney(
                  reportV3.baseline.total_proposed_amount,
                  reportV3.baseline.plan_currency
                )}
              </Text>
            </View>
            <Tag label={reportV3.baseline.plan_currency} tone="primary" />
          </View>
          <Text style={styles.cardText}>{reportV3.baseline.hypothetical_notice}</Text>
          {reportV3.baseline.holdings.map((holding) => (
            <View key={holding.id} style={styles.metadataRow}>
              <Text style={styles.metadataLabel}>{holding.symbol}</Text>
              <Text style={styles.metadataValue}>
                {formatPortfolioMoney(holding.proposed_amount, reportV3.baseline.plan_currency)} · {formatRatioPercent(Number(holding.target_allocation))}
              </Text>
            </View>
          ))}
          <Text style={styles.cardText}>
            Target weights come from proposed amounts. Estimated shares are for display only and do not affect this analysis.
          </Text>
        </Card>
      ) : reportV2 ? (
        <Card style={styles.snapshotCard}>
          <View style={styles.rowBetween}>
            <View style={{ flex: 1 }}>
              <Text style={styles.overline}>SAVED PORTFOLIO VALUATION</Text>
              <Text style={styles.snapshotValue}>
                {formatPortfolioMoney(
                  reportV2.valuation.total_current_value,
                  reportV2.valuation.valuation_currency
                )}
              </Text>
            </View>
            <Tag label={reportV2.valuation.valuation_currency} tone="primary" />
          </View>
          <Text style={styles.cardText}>
            Captured {reportV2.valuation.requested_date} using prices from {reportV2.valuation.oldest_price_as_of} to {reportV2.valuation.newest_price_as_of}. This saved context is not revalued.
          </Text>
          {historicalValue ? (
            <Text style={styles.cardText}>
              Same shares at historical prices: {formatPortfolioMoney(historicalValue.starting_value, historicalValue.currency)} on {historicalValue.start_date} → {formatPortfolioMoney(historicalValue.ending_value, historicalValue.currency)} on {historicalValue.end_date}
            </Text>
          ) : null}
          {reportV2.valuation.fx ? (
            <Text style={styles.cardText}>
              USD/THB {formatPortfolioQuantity(reportV2.valuation.fx.rate)} as of {reportV2.valuation.fx.as_of}
            </Text>
          ) : null}
        </Card>
      ) : (
        <Card style={styles.legacyCard}>
          <Text style={styles.overline}>SAVED LEGACY ALLOCATION</Text>
          <Text style={styles.cardText}>
            This older report uses the portfolio's saved allocation rather than current holding values.
          </Text>
        </Card>
      )}

      <View style={styles.metricGrid}>
        {reportV3 && monetary?.estimated_ending_value != null ? (
          <WebKpiCard
            icon="wallet-outline"
            label="Estimated Value at End of Period"
            value={formatPortfolioMoney(monetary.estimated_ending_value, monetary.currency)}
            meta="Historical estimate · Tap to understand"
            tone={metrics.cumulative_return < 0 ? 'danger' : 'success'}
            onPress={() => setSelectedMetric('endingValue')}
            accessibilityHint="Explains the estimated value and historical change"
          />
        ) : null}
        <WebKpiCard
          icon="speedometer-outline"
          label="Risk Score"
          value={`${risk.risk_score.toFixed(1)}/100`}
          meta={risk.risk_level}
          tone={riskTone(risk.risk_level)}
        />
        <WebKpiCard
          icon="trending-up-outline"
          label={portfolioReturnLabel}
          value={formatRatioPercent(metrics.cumulative_return)}
          meta={historicalValue
            ? monetary
              ? 'Same shares at historical prices · Tap for values'
              : 'Same shares valued across the saved period'
            : monetary
              ? 'Saved period · Tap for amount'
              : 'Saved period'}
          tone={metrics.cumulative_return < 0 ? 'danger' : 'success'}
          onPress={monetary ? () => setSelectedMetric('cumulative') : undefined}
          accessibilityHint={monetary ? 'Shows the percentage and estimated money amount' : undefined}
        />
        <WebKpiCard
          icon="analytics-outline"
          label="Annualized Return"
          value={formatRatioPercent(metrics.annualized_return)}
          meta={monetary ? 'Historical equivalent · Tap for amount' : 'Saved analysis'}
          tone={metrics.annualized_return < 0 ? 'danger' : 'success'}
          onPress={monetary ? () => setSelectedMetric('annualized') : undefined}
          accessibilityHint={monetary ? 'Shows the percentage and estimated annual money amount' : undefined}
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
          onPress={monetary?.maximum_drawdown_amount !== null && monetary?.maximum_drawdown_amount !== undefined
            ? () => setSelectedMetric('drawdown')
            : undefined}
          accessibilityHint={monetary?.maximum_drawdown_amount !== null && monetary?.maximum_drawdown_amount !== undefined
            ? 'Shows the percentage and estimated peak-to-trough money amount'
            : undefined}
        />
      </View>

      <SectionHeader title={reportV2 ? 'Historical Portfolio Return Series' : 'Portfolio Return Series'} />
      <Card style={styles.sectionCard}>
        <Text style={styles.cardText}>
          {historicalValue
            ? 'Returns calculated from the same share quantities at each historical price date.'
            : 'Historical periodic returns for the selected analysis period.'}
        </Text>
        <View style={styles.returnRangeTabs} accessibilityRole="tablist">
          {RETURN_VIEW_RANGES.map((range) => {
            const selected = range === returnViewRange;
            return (
              <Pressable
                key={range}
                accessibilityRole="tab"
                accessibilityState={{ selected }}
                onPress={() => setReturnViewRange(range)}
                style={({ pressed }) => [
                  styles.returnRangeButton,
                  selected && styles.returnRangeButtonActive,
                  pressed && styles.returnRangeButtonPressed
                ]}
              >
                <Text style={[styles.returnRangeText, selected && styles.returnRangeTextActive]}>{range}</Text>
              </Pressable>
            );
          })}
        </View>
        <PortfolioReturnsChart points={visibleReturns} />
        <Text style={styles.observationCount}>
          Showing {visibleReturns.length} of {analysis.portfolio_returns.length} return observations
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

      <SectionHeader title={reportV2 ? 'Per-Asset Valuation and Risk' : reportV3 ? 'Planned Asset Risk' : 'Individual Asset Metrics'} />
      <View style={styles.list}>
        {reportV2 ? reportV2.holdings.map((holding) => (
          <Pressable
            key={holding.id}
            accessibilityRole="button"
            accessibilityLabel={`Open ${holding.symbol} risk details`}
            disabled={!onOpenAsset}
            onPress={() => onOpenAsset?.(holding.symbol)}
            style={({ pressed }) => pressed && styles.assetCardPressed}
          >
          <Card style={styles.sectionCard}>
            <View style={styles.rowBetween}>
              <Text style={styles.assetSymbol}>{holding.symbol}</Text>
              <View style={styles.assetActionRow}>
                <Tag label={formatCurrentAllocation(holding.current_allocation)} tone="primary" />
                {onOpenAsset ? <Ionicons name="chevron-forward" size={19} color={colors.primary} /> : null}
              </View>
            </View>
            {holding.asset_metrics.risk_classification ? (
              <View style={styles.assetRiskRow}>
                <RiskBadge level={holding.asset_metrics.risk_classification.risk_level} />
                <Text style={styles.cardText}>{holding.asset_metrics.risk_classification.risk_score.toFixed(1)}/100</Text>
              </View>
            ) : null}
            <Text style={styles.cardText}>
              {formatPortfolioQuantity(holding.shares)} owned{holding.invested_amount && holding.invested_currency
                ? ` · invested ${holding.invested_currency} ${formatPortfolioQuantity(holding.invested_amount)}`
                : ''}{holding.purchase_date ? ` · purchased ${holding.purchase_date}` : ''}
            </Text>
            <View style={styles.dataGrid}>
              <Metric label="Saved current value" value={formatPortfolioMoney(holding.current_value, reportV2.valuation.valuation_currency)} />
              <Metric label="USD asset price" value={formatPortfolioMoney(holding.asset_price, 'USD')} />
              <Metric label="Price date" value={holding.price_as_of} />
              <Metric label="Cumulative return" value={formatRatioPercent(holding.asset_metrics.cumulative_return)} />
              <Metric label="Annualized return" value={formatRatioPercent(holding.asset_metrics.annualized_return)} />
              <Metric label="Asset volatility" value={formatRatioPercent(holding.asset_metrics.annualized_volatility)} />
              <Metric label="Max drawdown" value={formatRatioPercent(holding.asset_metrics.max_drawdown)} />
              <Metric label="Risk contribution" value={formatRatioPercent(holding.risk_driver.percentage_volatility_contribution)} />
            </View>
          </Card>
          </Pressable>
        )) : analysis.asset_metrics.map((asset) => (
          <Pressable
            key={asset.symbol}
            accessibilityRole="button"
            accessibilityLabel={`Open ${asset.symbol} risk details`}
            disabled={!onOpenAsset}
            onPress={() => onOpenAsset?.(asset.symbol)}
            style={({ pressed }) => pressed && styles.assetCardPressed}
          >
          <Card style={styles.sectionCard}>
            <View style={styles.rowBetween}>
              <Text style={styles.assetSymbol}>{asset.symbol}</Text>
              <View style={styles.assetActionRow}>
                <Tag label={formatRatioPercent(asset.weight)} tone="primary" />
                {onOpenAsset ? <Ionicons name="chevron-forward" size={19} color={colors.primary} /> : null}
              </View>
            </View>
            {asset.risk_classification ? (
              <View style={styles.assetRiskRow}>
                <RiskBadge level={asset.risk_classification.risk_level} />
                <Text style={styles.cardText}>{asset.risk_classification.risk_score.toFixed(1)}/100</Text>
              </View>
            ) : null}
            <View style={styles.dataGrid}>
              <Metric label="Cumulative return" value={formatRatioPercent(asset.cumulative_return)} />
              <Metric label="Annualized return" value={formatRatioPercent(asset.annualized_return)} />
              <Metric label="Volatility" value={formatRatioPercent(asset.annualized_volatility)} />
              <Metric label="Max drawdown" value={formatRatioPercent(asset.max_drawdown)} />
              <Metric label="Sharpe ratio" value={formatAnalysisNumber(asset.sharpe_ratio)} />
            </View>
          </Card>
          </Pressable>
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
        Historical analytics are educational, not investment recommendations. These metrics reflect the saved Aura analysis.
      </Text>
      <MetricAmountSheet
        content={reportMetricAmountContent(selectedMetric, report)}
        onClose={() => setSelectedMetric(null)}
      />
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
  snapshotCard: { gap: spacing.md, backgroundColor: colors.cyanBackground },
  plannedCard: { gap: spacing.md, backgroundColor: colors.summaryBackground, borderColor: colors.primary },
  legacyCard: { gap: spacing.sm, backgroundColor: colors.warningBackground },
  snapshotValue: { color: colors.text, fontSize: 24, fontWeight: '900', marginTop: spacing.xs },
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
  returnRangeTabs: { flexDirection: 'row', gap: spacing.xs },
  returnRangeButton: {
    flex: 1,
    minHeight: 34,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 9,
    backgroundColor: colors.surfaceAlt,
    alignItems: 'center',
    justifyContent: 'center'
  },
  returnRangeButtonActive: {
    borderColor: colors.primary,
    backgroundColor: colors.selectedBackground
  },
  returnRangeButtonPressed: { opacity: 0.78 },
  returnRangeText: { color: colors.textSecondary, fontSize: 10, fontWeight: '800' },
  returnRangeTextActive: { color: colors.primary },
  rowBetween: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: spacing.md
  },
  driverCard: { gap: spacing.md },
  driverTitle: { color: colors.text, fontSize: 16, fontWeight: '900' },
  assetSymbol: { color: colors.primary, fontSize: 18, fontWeight: '900' },
  assetActionRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  assetRiskRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  assetCardPressed: { opacity: 0.78, transform: [{ scale: 0.995 }] },
  scoreValue: { color: colors.primary, fontSize: 22, fontWeight: '900' },
  dataGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  metricItem: { flexGrow: 1, flexBasis: 132, gap: 3 },
  metricLabel: { color: colors.muted, fontSize: 9, lineHeight: 13 },
  metricValue: { color: colors.text, fontSize: 12, fontWeight: '900' },
  metadataRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
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
