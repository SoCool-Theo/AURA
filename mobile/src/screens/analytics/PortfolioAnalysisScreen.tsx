import React, { useState } from 'react';
import { Alert, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { PageTitle } from '../../components/ui/PageTitle';
import { SectionHeader } from '../../components/ui/SectionHeader';
import { WebKpiCard } from '../../components/ui/WebKpiCard';
import { DateRangeSelector, type DateRange } from '../../components/ui/DateRangeSelector';
import { RiskBadge } from '../../components/ui/RiskBadge';
import { AssetRelationshipBars } from '../../components/charts/AssetRelationshipBars';
import { DonutAllocationChart } from '../../components/charts/DonutAllocationChart';
import { useAppData } from '../../hooks/useAppData';
import { demoAnalyzePortfolio } from '../../utils/localCalculations';
import { colors, spacing } from '../../theme/theme';
import { formatPercent } from '../../utils/formatting';

export function PortfolioAnalysisScreen({ route }: { route: any }) {
  const { portfolios, activePortfolio, saveAnalysisReport } = useAppData();
  const [range, setRange] = useState<DateRange>('1Y');
  const portfolioId = route.params?.portfolioId ?? activePortfolio?.id;
  const portfolio = portfolios.find((item) => item.id === portfolioId);

  if (!portfolio) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.empty}><Text style={styles.emptyText}>Select a portfolio to view analytics.</Text></View>
      </SafeAreaView>
    );
  }

  const selectedPortfolio = portfolio;
  const analysis = demoAnalyzePortfolio(selectedPortfolio);

  async function saveReport() {
    const report = await saveAnalysisReport(selectedPortfolio.id);
    if (report) Alert.alert('Report saved', 'This analysis snapshot is now available in Reports.');
  }

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content}>
        <PageTitle eyebrow="PORTFOLIO ANALYSIS" title="Analytics" subtitle={`${selectedPortfolio.name} · detailed risk intelligence`} right={<RiskBadge level={analysis.riskLevel} />} />

        <Card style={styles.rangeCard}>
          <View style={styles.rangeHeader}><Text style={styles.rangeTitle}>Analysis period</Text><Text style={styles.rangeMeta}>Display preview</Text></View>
          <DateRangeSelector value={range} onChange={setRange} />
        </Card>

        <View style={styles.kpiGrid}>
          <WebKpiCard icon="speedometer-outline" label="Risk Score" value={`${analysis.riskScore}/100`} meta={analysis.riskLevel} tone={analysis.riskScore >= 70 ? 'danger' : 'warning'} />
          <WebKpiCard icon="pulse-outline" label="Volatility" value={formatPercent(analysis.volatility)} meta="Annualized" tone="warning" />
          <WebKpiCard icon="analytics-outline" label="Sharpe Ratio" value={analysis.sharpeRatio.toFixed(2)} meta="Risk-adjusted return" tone="blue" />
          <WebKpiCard icon="trending-down-outline" label="Max Drawdown" value={formatPercent(analysis.maxDrawdown)} meta="Historical downside" tone="danger" />
        </View>

        <SectionHeader title="Analysis Summary" />
        <Card style={styles.summaryCard}>
          <View style={styles.summaryIcon}><Ionicons name="shield-checkmark-outline" size={24} color={colors.primary} /></View>
          <View style={{ flex: 1 }}>
            <Text style={styles.summaryTitle}>{analysis.riskLevel}</Text>
            <Text style={styles.summaryText}>This portfolio combines {selectedPortfolio.holdings.length} holdings with {analysis.diversification.toLowerCase()} diversification. Review the risk drivers and asset relationships below for the main contributors.</Text>
          </View>
        </Card>

        <SectionHeader title="Risk Drivers" />
        <Card style={styles.tableCard}>
          <View style={styles.tableHeader}><Text style={[styles.tableHeaderText, { flex: 0.7 }]}>Asset</Text><Text style={[styles.tableHeaderText, { flex: 0.6 }]}>Level</Text><Text style={[styles.tableHeaderText, { flex: 1.7 }]}>Explanation</Text></View>
          {analysis.topRiskDrivers.map((driver, index) => (
            <View key={driver.symbol} style={[styles.driverRow, index > 0 && styles.borderTop]}>
              <View style={{ flex: 0.7 }}><Text style={styles.symbol}>{driver.symbol}</Text></View>
              <View style={{ flex: 0.6 }}><RiskBadge level={driver.level} /></View>
              <Text style={styles.driverText}>{driver.explanation}</Text>
            </View>
          ))}
        </Card>

        <SectionHeader title="Asset Relationships" />
        <Card>
          <Text style={styles.cardTitle}>Correlation relationships</Text>
          <Text style={styles.cardText}>A clearer mobile alternative to the web heatmap. The final values will come from backend market data.</Text>
          <View style={{ marginTop: spacing.lg }}><AssetRelationshipBars holdings={selectedPortfolio.holdings} /></View>
        </Card>

        <SectionHeader title="Diversification" />
        <Card style={styles.diversificationCard}>
          <View style={styles.diversificationScore}>
            <Text style={styles.overline}>STATUS</Text>
            <Text style={styles.diversificationValue}>{analysis.diversification}</Text>
            <Text style={styles.diversificationText}>Diversification reflects the mix of weights and risk characteristics in this demo frontend.</Text>
          </View>
          <DonutAllocationChart data={selectedPortfolio.holdings.map((holding) => ({ symbol: holding.symbol, weight: holding.weight }))} />
        </Card>

        <SectionHeader title="Individual Asset Analysis" />
        <View style={styles.assetList}>
          {selectedPortfolio.holdings.map((holding) => (
            <Card key={holding.symbol} style={styles.assetCard}>
              <View style={styles.assetTop}>
                <View style={styles.assetSymbolBox}><Text style={styles.assetSymbol}>{holding.symbol}</Text></View>
                <View style={{ flex: 1 }}><Text style={styles.assetName}>{holding.name}</Text><Text style={styles.assetMeta}>{holding.weight.toFixed(1)}% allocation</Text></View>
                <RiskBadge level={holding.risk} />
              </View>
              <View style={styles.assetMetrics}>
                <View><Text style={styles.assetMetricLabel}>Weight</Text><Text style={styles.assetMetricValue}>{holding.weight.toFixed(1)}%</Text></View>
                <View><Text style={styles.assetMetricLabel}>Risk</Text><Text style={styles.assetMetricValue}>{holding.risk}</Text></View>
                <View><Text style={styles.assetMetricLabel}>Contribution</Text><Text style={styles.assetMetricValue}>{holding.weight >= 30 ? 'High' : holding.weight >= 15 ? 'Medium' : 'Lower'}</Text></View>
              </View>
            </Card>
          ))}
        </View>

        <Button title="Save Analysis Report" onPress={saveReport} style={{ marginTop: spacing.xl }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 100 },
  rangeCard: { marginTop: spacing.xl, gap: spacing.md },
  rangeHeader: { flexDirection: 'row', justifyContent: 'space-between' },
  rangeTitle: { color: colors.text, fontSize: 12, fontWeight: '900' },
  rangeMeta: { color: colors.muted, fontSize: 9 },
  kpiGrid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', gap: spacing.md, marginTop: spacing.md },
  summaryCard: { flexDirection: 'row', gap: spacing.md, alignItems: 'flex-start' },
  summaryIcon: { width: 48, height: 48, borderRadius: 15, backgroundColor: colors.cyanBackground, alignItems: 'center', justifyContent: 'center' },
  summaryTitle: { color: colors.text, fontSize: 16, fontWeight: '900' },
  summaryText: { color: colors.textSecondary, fontSize: 12, lineHeight: 18, marginTop: 5 },
  tableCard: { paddingVertical: spacing.sm },
  tableHeader: { flexDirection: 'row', gap: spacing.sm, paddingBottom: spacing.sm },
  tableHeaderText: { color: colors.muted, fontSize: 8, fontWeight: '900', textTransform: 'uppercase', letterSpacing: 0.7 },
  driverRow: { flexDirection: 'row', gap: spacing.sm, alignItems: 'flex-start', paddingVertical: spacing.md },
  borderTop: { borderTopWidth: 1, borderTopColor: colors.borderSoft },
  symbol: { color: colors.primary, fontSize: 11, fontWeight: '900' },
  driverText: { color: colors.textSecondary, fontSize: 10, lineHeight: 15, flex: 1.7 },
  cardTitle: { color: colors.text, fontSize: 14, fontWeight: '900' },
  cardText: { color: colors.textSecondary, fontSize: 11, lineHeight: 17, marginTop: 4 },
  diversificationCard: { gap: spacing.lg },
  diversificationScore: { gap: 4 },
  overline: { color: colors.muted, fontSize: 9, fontWeight: '900', letterSpacing: 1 },
  diversificationValue: { color: colors.text, fontSize: 22, fontWeight: '900' },
  diversificationText: { color: colors.textSecondary, fontSize: 11, lineHeight: 17 },
  assetList: { gap: spacing.md },
  assetCard: { gap: spacing.md },
  assetTop: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  assetSymbolBox: { minWidth: 52, paddingHorizontal: 8, height: 42, borderRadius: 13, backgroundColor: colors.surfaceAlt, alignItems: 'center', justifyContent: 'center' },
  assetSymbol: { color: colors.primary, fontSize: 10, fontWeight: '900' },
  assetName: { color: colors.text, fontSize: 13, fontWeight: '900' },
  assetMeta: { color: colors.muted, fontSize: 10, marginTop: 3 },
  assetMetrics: { flexDirection: 'row', justifyContent: 'space-between', borderTopWidth: 1, borderTopColor: colors.borderSoft, paddingTop: spacing.md },
  assetMetricLabel: { color: colors.muted, fontSize: 9 },
  assetMetricValue: { color: colors.text, fontSize: 11, fontWeight: '900', marginTop: 3 },
  empty: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  emptyText: { color: colors.textSecondary }
});
