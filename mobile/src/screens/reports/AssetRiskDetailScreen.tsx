import React, { useCallback, useState } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { PortfolioReturnsChart } from '../../components/charts/PortfolioReturnsChart';
import { Card } from '../../components/ui/Card';
import { LoadingState } from '../../components/ui/LoadingState';
import { PageTitle } from '../../components/ui/PageTitle';
import { RiskBadge } from '../../components/ui/RiskBadge';
import { ScreenErrorState } from '../../components/ui/ErrorState';
import {
  filterReturnPoints,
  RETURN_VIEW_RANGES,
  type ReturnViewRange
} from '../../dashboard/dashboardPresentation';
import {
  formatCurrentAllocation,
  formatPortfolioMoney,
  formatPortfolioQuantity
} from '../../portfolio/portfolioFormatting';
import {
  formatAnalysisNumber,
  formatRatioPercent
} from '../../report/reportFormatting';
import { useReports } from '../../report/useReports';
import { colors, spacing } from '../../theme/theme';
import {
  isPortfolioReportV2,
  isPortfolioReportV3,
  type PortfolioReportResponse
} from '../../types/report';

type LoadStatus = 'loading' | 'ready' | 'error';

export function AssetRiskDetailScreen({
  route,
  navigation
}: {
  route: any;
  navigation: any;
}) {
  const portfolioId = route.params.portfolioId as string;
  const reportId = route.params.reportId as string;
  const assetSymbol = (route.params.assetSymbol as string).toUpperCase();
  const { getReport } = useReports();
  const [report, setReport] = useState<PortfolioReportResponse | null>(null);
  const [status, setStatus] = useState<LoadStatus>('loading');
  const [error, setError] = useState<unknown>(null);
  const [range, setRange] = useState<ReturnViewRange>('1Y');

  const loadReport = useCallback(async () => {
    setStatus('loading');
    setError(null);
    try {
      setReport(await getReport(portfolioId, reportId));
      setStatus('ready');
    } catch (requestError) {
      setError(requestError);
      setStatus('error');
    }
  }, [getReport, portfolioId, reportId]);

  useFocusEffect(useCallback(() => {
    void loadReport();
  }, [loadReport]));

  if (status === 'loading' && !report) {
    return <LoadingState message="Loading asset risk…" />;
  }

  if (!report) {
    return (
      <SafeAreaView style={styles.safe} edges={['bottom']}>
        <ScreenErrorState
          error={error}
          resourceName="Asset analysis"
          fallbackMessage="Unable to load this saved asset analysis."
          onRetry={() => void loadReport()}
          onBack={() => navigation.goBack()}
        />
      </SafeAreaView>
    );
  }

  const asset = report.analysis.asset_metrics.find(
    (metric) => metric.symbol === assetSymbol
  );
  if (!asset) {
    return (
      <SafeAreaView style={styles.safe} edges={['bottom']}>
        <ScreenErrorState
          error={`${assetSymbol} is not part of this saved report.`}
          resourceName="Asset analysis"
          fallbackMessage="Asset analysis not found."
          onBack={() => navigation.goBack()}
        />
      </SafeAreaView>
    );
  }

  const risk = asset.risk_classification;
  const series = report.analysis.asset_returns?.find(
    (item) => item.symbol === assetSymbol
  );
  const visiblePoints = filterReturnPoints(series?.points ?? [], range);
  const driver = report.analysis.risk_drivers.entries.find(
    (entry) => entry.symbol === assetSymbol
  );
  const reportV2 = isPortfolioReportV2(report) ? report : null;
  const reportV3 = isPortfolioReportV3(report) ? report : null;
  const currentHolding = reportV2?.holdings.find(
    (holding) => holding.symbol === assetSymbol
  );
  const plannedHolding = reportV3?.baseline.holdings.find(
    (holding) => holding.symbol === assetSymbol
  );

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content}>
        <PageTitle
          eyebrow="ASSET RISK DETAIL"
          title={assetSymbol}
          subtitle={`${report.analysis.portfolio_name} · immutable saved analysis`}
        />

        <Card style={styles.riskCard}>
          <View style={styles.riskHeader}>
            <View style={styles.assetMark}>
              <Text style={styles.assetMarkText}>{assetSymbol.slice(0, 4)}</Text>
            </View>
            <View style={styles.riskTitle}>
              <Text style={styles.overline}>HISTORICAL ASSET RISK</Text>
              <Text style={styles.score}>{risk ? `${risk.risk_score.toFixed(1)}/100` : 'N/A'}</Text>
            </View>
            {risk ? <RiskBadge level={risk.risk_level} /> : null}
          </View>
          {risk ? risk.reasons.map((reason, index) => (
            <Text key={`${index}-${reason}`} style={styles.reason}>• {reason}</Text>
          )) : (
            <Text style={styles.cardText}>This older report predates per-asset risk classification.</Text>
          )}
        </Card>

        <View style={styles.metricGrid}>
          <Metric label="Portfolio weight" value={formatRatioPercent(asset.weight)} />
          <Metric label="Cumulative return" value={formatRatioPercent(asset.cumulative_return)} />
          <Metric label="Annualized return" value={formatRatioPercent(asset.annualized_return)} />
          <Metric label="Annualized volatility" value={formatRatioPercent(asset.annualized_volatility)} />
          <Metric label="Maximum drawdown" value={formatRatioPercent(asset.max_drawdown)} />
          <Metric label="Sharpe ratio" value={formatAnalysisNumber(asset.sharpe_ratio)} />
        </View>

        <Text style={styles.sectionTitle}>Historical Return Series</Text>
        <Card style={styles.sectionCard}>
          <Text style={styles.cardText}>Periodic {assetSymbol} returns frozen with this report.</Text>
          {series?.points.length ? <>
            <View style={styles.returnRangeTabs} accessibilityRole="tablist">
              {RETURN_VIEW_RANGES.map((option) => {
                const selected = option === range;
                return (
                  <Pressable
                    key={option}
                    accessibilityRole="tab"
                    accessibilityState={{ selected }}
                    onPress={() => setRange(option)}
                    style={({ pressed }) => [
                      styles.rangeButton,
                      selected && styles.rangeButtonActive,
                      pressed && styles.pressed
                    ]}
                  >
                    <Text style={[styles.rangeText, selected && styles.rangeTextActive]}>{option}</Text>
                  </Pressable>
                );
              })}
            </View>
            <PortfolioReturnsChart points={visiblePoints} />
            <Text style={styles.observationCount}>Showing {visiblePoints.length} of {series.points.length} saved observations</Text>
          </> : (
            <View style={styles.emptyGraph}>
              <Ionicons name="time-outline" size={26} color={colors.primary} />
              <Text style={styles.emptyTitle}>Historical asset graph unavailable</Text>
              <Text style={styles.emptyText}>This report was created before per-asset series were stored. Run a new analysis to create the graph.</Text>
            </View>
          )}
        </Card>

        <Text style={styles.sectionTitle}>Portfolio Impact</Text>
        <Card style={styles.sectionCard}>
          {driver ? <>
            <Detail label="Risk-driver rank" value={`#${driver.rank}`} />
            <Detail label="Risk contribution" value={formatRatioPercent(driver.percentage_volatility_contribution)} />
            <Detail label="Component contribution" value={formatRatioPercent(driver.component_volatility_contribution)} />
            <Detail label="Marginal contribution" value={formatRatioPercent(driver.marginal_volatility_contribution)} />
          </> : <Text style={styles.cardText}>Portfolio-impact details are unavailable.</Text>}
        </Card>

        <Text style={styles.sectionTitle}>Saved Position</Text>
        <Card style={styles.sectionCard}>
          {currentHolding && reportV2 ? <>
            <Detail label="Current value" value={formatPortfolioMoney(currentHolding.current_value, reportV2.valuation.valuation_currency)} />
            <Detail label="Shares" value={formatPortfolioQuantity(currentHolding.shares)} />
            <Detail label="Saved allocation" value={formatCurrentAllocation(currentHolding.current_allocation)} />
            <Detail label="Price date" value={currentHolding.price_as_of} />
          </> : plannedHolding && reportV3 ? <>
            <Detail label="Proposed amount" value={formatPortfolioMoney(plannedHolding.proposed_amount, reportV3.baseline.plan_currency)} />
            <Detail label="Target allocation" value={formatCurrentAllocation(plannedHolding.target_allocation)} />
            <Detail label="Portfolio mode" value="Hypothetical plan" />
          </> : <Detail label="Saved allocation" value={formatRatioPercent(asset.weight)} />}
        </Card>

        <Text style={styles.education}>Historical asset analytics are educational, not forecasts or investment recommendations.</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <Card style={styles.metric}><Text style={styles.metricLabel}>{label}</Text><Text style={styles.metricValue}>{value}</Text></Card>;
}

function Detail({ label, value }: { label: string; value: string }) {
  return <View style={styles.detailRow}><Text style={styles.detailLabel}>{label}</Text><Text style={styles.detailValue}>{value}</Text></View>;
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 110 },
  riskCard: { gap: spacing.sm, marginTop: spacing.xl, backgroundColor: colors.summaryBackground },
  riskHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  assetMark: { width: 52, height: 52, borderRadius: 15, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.selectedBackground, borderWidth: 1, borderColor: colors.primary },
  assetMarkText: { color: colors.primary, fontSize: 12, fontWeight: '900' },
  riskTitle: { flex: 1 },
  overline: { color: colors.primary, fontSize: 9, fontWeight: '900', letterSpacing: 1 },
  score: { color: colors.text, fontSize: 25, fontWeight: '900', marginTop: 4 },
  reason: { color: colors.textSecondary, fontSize: 11, lineHeight: 17 },
  cardText: { color: colors.textSecondary, fontSize: 11, lineHeight: 17 },
  metricGrid: { marginTop: spacing.md, flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  metric: { flexGrow: 1, flexBasis: 145, minHeight: 86, gap: spacing.sm },
  metricLabel: { color: colors.muted, fontSize: 9, textTransform: 'uppercase' },
  metricValue: { color: colors.text, fontSize: 18, fontWeight: '900' },
  sectionTitle: { color: colors.text, fontSize: 16, fontWeight: '900', marginTop: spacing.xl, marginBottom: spacing.sm },
  sectionCard: { gap: spacing.md },
  returnRangeTabs: { flexDirection: 'row', gap: spacing.xs },
  rangeButton: { flex: 1, minHeight: 36, borderWidth: 1, borderColor: colors.border, borderRadius: 9, backgroundColor: colors.surfaceAlt, alignItems: 'center', justifyContent: 'center' },
  rangeButtonActive: { borderColor: colors.primary, backgroundColor: colors.selectedBackground },
  rangeText: { color: colors.textSecondary, fontSize: 10, fontWeight: '800' },
  rangeTextActive: { color: colors.primary },
  pressed: { opacity: 0.78 },
  observationCount: { color: colors.muted, fontSize: 10, textAlign: 'center' },
  emptyGraph: { minHeight: 180, alignItems: 'center', justifyContent: 'center', padding: spacing.lg },
  emptyTitle: { color: colors.text, fontSize: 14, fontWeight: '900', marginTop: spacing.sm },
  emptyText: { color: colors.muted, fontSize: 10, lineHeight: 16, textAlign: 'center', marginTop: spacing.xs },
  detailRow: { minHeight: 42, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: spacing.md, borderTopWidth: 1, borderTopColor: colors.borderSoft },
  detailLabel: { color: colors.muted, fontSize: 10, flex: 1 },
  detailValue: { color: colors.text, fontSize: 11, fontWeight: '900', textAlign: 'right', flex: 1 },
  education: { color: colors.muted, fontSize: 10, lineHeight: 16, textAlign: 'center', marginTop: spacing.xl }
});
