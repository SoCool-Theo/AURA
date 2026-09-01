import React, { useMemo, useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { PageTitle } from '../../components/ui/PageTitle';
import { SectionHeader } from '../../components/ui/SectionHeader';
import { SegmentedTabs } from '../../components/ui/SegmentedTabs';
import { WebKpiCard } from '../../components/ui/WebKpiCard';
import { RiskBadge } from '../../components/ui/RiskBadge';
import { PortfolioPerformanceChart } from '../../components/charts/PortfolioPerformanceChart';
import { DonutAllocationChart } from '../../components/charts/DonutAllocationChart';
import { useAppData } from '../../hooks/useAppData';
import { usePreferences } from '../../preferences/usePreferences';
import { demoAnalyzePortfolio } from '../../utils/localCalculations';
import { colors, spacing } from '../../theme/theme';
import { formatCurrency, formatPercent } from '../../utils/formatting';

const tabs = ['Overview', 'Holdings', 'Performance', 'Activity'] as const;
type Tab = (typeof tabs)[number];

export function PortfolioDetailScreen({ route, navigation }: { route: any; navigation: any }) {
  const {
    portfolios,
    reports,
    simulations,
    duplicatePortfolio,
    deletePortfolio,
    setActivePortfolio
  } = useAppData();
  const { hidePortfolioValues } = usePreferences();
  const [tab, setTab] = useState<Tab>('Overview');

  const portfolio = portfolios.find((item) => item.id === route.params.portfolioId);
  const activities = useMemo(() => {
    if (!portfolio) return [];
    const reportEvents = reports
      .filter((item) => item.portfolioId === portfolio.id)
      .map((item) => ({ id: item.id, title: 'Analysis report saved', subtitle: 'Risk analysis snapshot', date: item.createdAt, icon: 'document-text-outline' as const }));
    const simulationEvents = simulations
      .filter((item) => item.portfolioId === portfolio.id)
      .map((item) => ({ id: item.id, title: item.mode, subtitle: item.title, date: item.createdAt, icon: 'pulse-outline' as const }));
    return [...reportEvents, ...simulationEvents].sort((a, b) => b.date.localeCompare(a.date));
  }, [portfolio, reports, simulations]);

  if (!portfolio) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.empty}><Text style={styles.emptyText}>Portfolio not found.</Text></View>
      </SafeAreaView>
    );
  }

  const selectedPortfolio = portfolio;
  const analysis = demoAnalyzePortfolio(selectedPortfolio);
  const money = (value: number) => hidePortfolioValues ? '••••••' : formatCurrency(value);

  async function duplicate() {
    const copy = await duplicatePortfolio(selectedPortfolio.id);
    if (copy) navigation.replace('PortfolioDetail', { portfolioId: copy.id });
  }

  function confirmDelete() {
    Alert.alert('Delete portfolio?', 'This removes the local portfolio and its holdings.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          await deletePortfolio(selectedPortfolio.id);
          navigation.popToTop();
        }
      }
    ]);
  }

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content}>
        <PageTitle
          title={selectedPortfolio.name}
          subtitle={`${selectedPortfolio.holdings.length} holdings · ${money(selectedPortfolio.totalValue)}`}
          right={<RiskBadge level={analysis.riskLevel} />}
        />

        <View style={styles.actions}>
          <Button title="Analyze Portfolio" style={{ flex: 1.3 }} onPress={() => navigation.navigate('PortfolioAnalysis', { portfolioId: selectedPortfolio.id })} />
          <Button title="Add Asset" variant="secondary" style={{ flex: 1 }} onPress={() => navigation.navigate('AddAsset', { portfolioId: selectedPortfolio.id })} />
        </View>

        <SegmentedTabs items={tabs} value={tab} onChange={setTab} />

        {tab === 'Overview' ? (
          <>
            <View style={styles.kpiGrid}>
              <WebKpiCard icon="wallet-outline" label="Portfolio Value" value={money(selectedPortfolio.totalValue)} meta={`${selectedPortfolio.holdings.length} holdings`} tone="blue" />
              <WebKpiCard icon="speedometer-outline" label="Risk Score" value={`${analysis.riskScore}/100`} meta={analysis.riskLevel} tone={analysis.riskScore >= 70 ? 'danger' : 'warning'} />
              <WebKpiCard icon="trending-up-outline" label="Annualized Return" value={formatPercent(analysis.annualizedReturn)} meta="Demo analysis" tone="success" />
              <WebKpiCard icon="trending-down-outline" label="Max Drawdown" value={formatPercent(analysis.maxDrawdown)} meta="Downside" tone="danger" />
            </View>

            <SectionHeader title="Allocation" action="Edit holdings" onPress={() => navigation.navigate('EditHoldings', { portfolioId: selectedPortfolio.id })} />
            <Card><DonutAllocationChart data={selectedPortfolio.holdings.map((holding) => ({ symbol: holding.symbol, weight: holding.weight }))} /></Card>

            <SectionHeader title="Risk Summary" />
            <Card style={styles.summaryCard}>
              <View style={styles.summaryRow}><Text style={styles.summaryLabel}>Volatility</Text><Text style={styles.summaryValue}>{formatPercent(analysis.volatility)}</Text></View>
              <View style={styles.summaryRow}><Text style={styles.summaryLabel}>Sharpe Ratio</Text><Text style={styles.summaryValue}>{analysis.sharpeRatio.toFixed(2)}</Text></View>
              <View style={styles.summaryRow}><Text style={styles.summaryLabel}>Diversification</Text><Text style={styles.summaryValue}>{analysis.diversification}</Text></View>
            </Card>
          </>
        ) : null}

        {tab === 'Holdings' ? (
          <>
            <SectionHeader title="Holdings" action="Edit" onPress={() => navigation.navigate('EditHoldings', { portfolioId: selectedPortfolio.id })} />
            <View style={styles.list}>
              {selectedPortfolio.holdings.map((holding) => (
                <Card key={holding.symbol} style={styles.holdingRow}>
                  <View style={styles.symbolBadge}><Text style={styles.symbolBadgeText}>{holding.symbol}</Text></View>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.holdingName}>{holding.name}</Text>
                    <Text style={styles.holdingMeta}>{holding.risk} risk</Text>
                  </View>
                  <View style={styles.holdingRight}>
                    <Text style={styles.holdingValue}>{money(holding.value)}</Text>
                    <Text style={styles.weight}>{holding.weight.toFixed(1)}%</Text>
                  </View>
                </Card>
              ))}
            </View>
            <Button title="Add Asset" variant="secondary" onPress={() => navigation.navigate('AddAsset', { portfolioId: selectedPortfolio.id })} style={{ marginTop: spacing.md }} />
          </>
        ) : null}

        {tab === 'Performance' ? (
          <>
            <SectionHeader title="Performance" />
            <Card style={styles.performanceCard}>
              <View style={styles.performanceSummary}>
                <View><Text style={styles.overline}>ANNUALIZED RETURN</Text><Text style={styles.positive}>{formatPercent(analysis.annualizedReturn)}</Text></View>
                <View style={{ alignItems: 'flex-end' }}><Text style={styles.overline}>BENCHMARK</Text><Text style={styles.benchmark}>+8.32%</Text></View>
              </View>
              <PortfolioPerformanceChart />
            </Card>
          </>
        ) : null}

        {tab === 'Activity' ? (
          <>
            <SectionHeader title="Recent Activity" />
            {activities.length ? (
              <View style={styles.list}>
                {activities.map((item) => (
                  <Card key={item.id} style={styles.activityRow}>
                    <View style={styles.activityIcon}><Ionicons name={item.icon} size={19} color={colors.primary} /></View>
                    <View style={{ flex: 1 }}><Text style={styles.activityTitle}>{item.title}</Text><Text style={styles.activityText}>{item.subtitle}</Text></View>
                    <Text style={styles.activityDate}>{new Date(item.date).toLocaleDateString()}</Text>
                  </Card>
                ))}
              </View>
            ) : (
              <Card style={styles.emptyCard}><Text style={styles.emptyCardTitle}>No activity yet</Text><Text style={styles.emptyCardText}>Run an analysis or simulation and it will appear here.</Text></Card>
            )}
          </>
        ) : null}

        <SectionHeader title="Portfolio Actions" />
        <View style={styles.actionGrid}>
          <Button title="Set Active" variant="secondary" style={{ flex: 1 }} onPress={() => setActivePortfolio(selectedPortfolio.id)} />
          <Button title="Duplicate" variant="secondary" style={{ flex: 1 }} onPress={duplicate} />
        </View>
        <Button title="Delete Portfolio" variant="danger" style={{ marginTop: spacing.md }} onPress={confirmDelete} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 100 },
  actions: { flexDirection: 'row', gap: spacing.md, marginTop: spacing.xl, marginBottom: spacing.md },
  kpiGrid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', gap: spacing.md, marginTop: spacing.xl },
  summaryCard: { gap: spacing.md },
  summaryRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingBottom: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.borderSoft },
  summaryLabel: { color: colors.textSecondary, fontSize: 11 },
  summaryValue: { color: colors.text, fontSize: 13, fontWeight: '900' },
  list: { gap: spacing.md },
  holdingRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  symbolBadge: { minWidth: 54, paddingHorizontal: 8, height: 42, borderRadius: 13, backgroundColor: colors.cyanBackground, alignItems: 'center', justifyContent: 'center' },
  symbolBadgeText: { color: colors.primary, fontSize: 10, fontWeight: '900' },
  holdingName: { color: colors.text, fontSize: 13, fontWeight: '900' },
  holdingMeta: { color: colors.muted, fontSize: 10, marginTop: 3 },
  holdingRight: { alignItems: 'flex-end' },
  holdingValue: { color: colors.text, fontSize: 12, fontWeight: '900' },
  weight: { color: colors.primary, fontSize: 10, fontWeight: '800', marginTop: 3 },
  performanceCard: { gap: spacing.md },
  performanceSummary: { flexDirection: 'row', justifyContent: 'space-between' },
  overline: { color: colors.muted, fontSize: 9, fontWeight: '900', letterSpacing: 0.9 },
  positive: { color: colors.success, fontSize: 20, fontWeight: '900', marginTop: 4 },
  benchmark: { color: colors.textSecondary, fontSize: 15, fontWeight: '900', marginTop: 4 },
  activityRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  activityIcon: { width: 42, height: 42, borderRadius: 13, backgroundColor: colors.cyanBackground, alignItems: 'center', justifyContent: 'center' },
  activityTitle: { color: colors.text, fontSize: 12, fontWeight: '900' },
  activityText: { color: colors.textSecondary, fontSize: 10, marginTop: 3 },
  activityDate: { color: colors.muted, fontSize: 9 },
  emptyCard: { alignItems: 'center', paddingVertical: spacing.xxl },
  emptyCardTitle: { color: colors.text, fontWeight: '900' },
  emptyCardText: { color: colors.muted, fontSize: 11, marginTop: 4, textAlign: 'center' },
  actionGrid: { flexDirection: 'row', gap: spacing.md },
  empty: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  emptyText: { color: colors.textSecondary }
});
