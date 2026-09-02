import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import { Card } from '../../components/ui/Card';
import { PageTitle } from '../../components/ui/PageTitle';
import { SectionHeader } from '../../components/ui/SectionHeader';
import { WebKpiCard } from '../../components/ui/WebKpiCard';
import { DateRangeSelector, type DateRange } from '../../components/ui/DateRangeSelector';
import { PortfolioPerformanceChart } from '../../components/charts/PortfolioPerformanceChart';
import { DonutAllocationChart } from '../../components/charts/DonutAllocationChart';
import { RiskBadge } from '../../components/ui/RiskBadge';
import { useAppData } from '../../hooks/useAppData';
import { usePreferences } from '../../preferences/usePreferences';
import { demoAnalyzePortfolio } from '../../utils/localCalculations';
import { colors, spacing } from '../../theme/theme';
import { formatCurrency, formatPercent } from '../../utils/formatting';

export function DashboardScreen({ navigation }: { navigation: any }) {
  const { displayName, hidePortfolioValues } = usePreferences();
  const { activePortfolio, portfolios, setActivePortfolio } = useAppData();
  const [range, setRange] = useState<DateRange>('1Y');

  if (!activePortfolio) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.empty}>
          <PageTitle title="Welcome to Aura" subtitle="Create a portfolio to start your risk dashboard." />
          <Pressable style={styles.primaryAction} onPress={() => navigation.navigate('Portfolio', { screen: 'CreatePortfolio' })}>
            <Text style={styles.primaryActionText}>Create Portfolio</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  const portfolio = activePortfolio;
  const analysis = demoAnalyzePortfolio(portfolio);
  const firstName = (displayName || 'Investor').split(' ')[0];
  const showMoney = (value: number) => hidePortfolioValues ? '••••••' : formatCurrency(value);

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content}>
        <PageTitle
          eyebrow="AURA"
          title={`Welcome back, ${firstName}`}
          subtitle="Here is your portfolio overview."
          right={
            <Pressable style={styles.profileButton} onPress={() => navigation.navigate('MoreTab', { screen: 'Settings' })}>
              <Ionicons name="person-outline" size={19} color={colors.text} />
            </Pressable>
          }
        />

        <Card style={styles.selectorCard}>
          <View style={styles.selectorHeader}>
            <View>
              <Text style={styles.overline}>PORTFOLIO</Text>
              <Text style={styles.selectorName}>{portfolio.name}</Text>
            </View>
            <RiskBadge level={analysis.riskLevel} />
          </View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.portfolioChips}>
            {portfolios.map((item) => {
              const active = item.id === portfolio.id;
              return (
                <Pressable key={item.id} onPress={() => setActivePortfolio(item.id)} style={[styles.portfolioChip, active && styles.portfolioChipActive]}>
                  <Text style={[styles.portfolioChipText, active && styles.portfolioChipTextActive]}>{item.name}</Text>
                </Pressable>
              );
            })}
          </ScrollView>
        </Card>

        <View style={styles.kpiGrid}>
          <WebKpiCard icon="wallet-outline" label="Total Portfolio Value" value={showMoney(portfolio.totalValue)} meta={`${portfolio.holdings.length} holdings`} tone="blue" />
          <WebKpiCard icon="speedometer-outline" label="Risk Score" value={`${analysis.riskScore}/100`} meta={analysis.riskLevel} tone={analysis.riskScore >= 70 ? 'danger' : analysis.riskScore >= 40 ? 'warning' : 'success'} />
          <WebKpiCard icon="trending-up-outline" label="Annualized Return" value={formatPercent(analysis.annualizedReturn)} meta="Portfolio return" tone="success" />
          <WebKpiCard icon="trending-down-outline" label="Maximum Drawdown" value={formatPercent(analysis.maxDrawdown)} meta="Peak-to-trough" tone="danger" />
        </View>

        <SectionHeader title="Portfolio Performance" action="Analytics" onPress={() => navigation.navigate('MoreTab', { screen: 'Analytics', params: { portfolioId: portfolio.id } })} />
        <Card style={styles.performanceCard}>
          <DateRangeSelector value={range} onChange={setRange} />
          <View style={styles.performanceHeader}>
            <View>
              <Text style={styles.overline}>{range} PERFORMANCE</Text>
              <Text style={styles.performanceValue}>{formatPercent(analysis.annualizedReturn)}</Text>
            </View>
            <Text style={styles.benchmarkText}>Benchmark +8.32%</Text>
          </View>
          <PortfolioPerformanceChart />
        </Card>

        <SectionHeader title="Top Risk Drivers" action="View all" onPress={() => navigation.navigate('MoreTab', { screen: 'Analytics', params: { portfolioId: portfolio.id } })} />
        <Card>
          {analysis.topRiskDrivers.slice(0, 3).map((driver, index) => (
            <View key={driver.symbol} style={[styles.riskRow, index > 0 && styles.rowBorder]}>
              <View style={styles.symbolBox}><Text style={styles.symbolText}>{driver.symbol}</Text></View>
              <View style={{ flex: 1 }}>
                <Text style={styles.riskTitle}>{driver.symbol}</Text>
                <Text style={styles.riskExplanation}>{driver.explanation}</Text>
              </View>
              <RiskBadge level={driver.level} />
            </View>
          ))}
        </Card>

        <SectionHeader title="Portfolio Allocation" />
        <Card>
          <DonutAllocationChart data={portfolio.holdings.map((holding) => ({ symbol: holding.symbol, weight: holding.weight }))} />
        </Card>

        <SectionHeader title="AI Insight" />
        <Card style={styles.aiCard}>
          <View style={styles.aiIcon}><Ionicons name="sparkles-outline" size={22} color={colors.primary} /></View>
          <View style={{ flex: 1 }}>
            <Text style={styles.aiTitle}>Explain this portfolio with Aura</Text>
            <Text style={styles.aiText}>The AI interface is ready. Real explanations remain unavailable until the backend AI Agent is connected.</Text>
            <Pressable onPress={() => navigation.navigate('AI')} style={styles.inlineLink}>
              <Text style={styles.inlineLinkText}>Open AI Assistant</Text>
              <Ionicons name="arrow-forward" size={15} color={colors.primary} />
            </Pressable>
          </View>
        </Card>

        <SectionHeader title="Portfolio Analysis" />
        <Pressable onPress={() => navigation.navigate('MoreTab', { screen: 'Analytics', params: { portfolioId: portfolio.id } })}>
          <Card style={styles.analysisCard}>
            <View style={styles.analysisIcon}><Ionicons name="analytics-outline" size={24} color={colors.blue} /></View>
            <View style={{ flex: 1 }}>
              <Text style={styles.analysisTitle}>Detailed Risk Analysis</Text>
              <Text style={styles.analysisText}>Volatility, Sharpe ratio, diversification, asset relationships and individual asset risk.</Text>
            </View>
            <Ionicons name="chevron-forward" color={colors.muted} size={20} />
          </Card>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 110 },
  profileButton: { width: 40, height: 40, borderRadius: 13, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSoft, alignItems: 'center', justifyContent: 'center' },
  selectorCard: { marginTop: spacing.xl, gap: spacing.md },
  selectorHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: spacing.md },
  overline: { color: colors.muted, fontSize: 9, fontWeight: '900', letterSpacing: 1.1 },
  selectorName: { color: colors.text, fontSize: 17, fontWeight: '900', marginTop: 4 },
  portfolioChips: { gap: spacing.sm },
  portfolioChip: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 999, backgroundColor: colors.surfaceAlt, borderWidth: 1, borderColor: colors.borderSoft },
  portfolioChipActive: { backgroundColor: colors.selectedBackground, borderColor: colors.primary },
  portfolioChipText: { color: colors.textSecondary, fontSize: 10, fontWeight: '800' },
  portfolioChipTextActive: { color: colors.primary },
  kpiGrid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', gap: spacing.md, marginTop: spacing.md },
  performanceCard: { gap: spacing.md },
  performanceHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end' },
  performanceValue: { color: colors.success, fontSize: 22, fontWeight: '900', marginTop: 4 },
  benchmarkText: { color: colors.textSecondary, fontSize: 10, fontWeight: '700' },
  riskRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, paddingVertical: spacing.md },
  rowBorder: { borderTopWidth: 1, borderTopColor: colors.borderSoft },
  symbolBox: { minWidth: 48, paddingHorizontal: 8, height: 40, borderRadius: 12, backgroundColor: colors.surfaceAlt, alignItems: 'center', justifyContent: 'center' },
  symbolText: { color: colors.primary, fontSize: 10, fontWeight: '900' },
  riskTitle: { color: colors.text, fontWeight: '900' },
  riskExplanation: { color: colors.textSecondary, fontSize: 11, lineHeight: 16, marginTop: 3 },
  aiCard: { flexDirection: 'row', gap: spacing.md, alignItems: 'flex-start' },
  aiIcon: { width: 46, height: 46, borderRadius: 15, backgroundColor: colors.cyanBackground, alignItems: 'center', justifyContent: 'center' },
  aiTitle: { color: colors.text, fontSize: 15, fontWeight: '900' },
  aiText: { color: colors.textSecondary, fontSize: 12, lineHeight: 18, marginTop: 5 },
  inlineLink: { flexDirection: 'row', gap: 6, alignItems: 'center', marginTop: spacing.md },
  inlineLinkText: { color: colors.primary, fontSize: 11, fontWeight: '900' },
  analysisCard: { flexDirection: 'row', gap: spacing.md, alignItems: 'center' },
  analysisIcon: { width: 48, height: 48, borderRadius: 15, backgroundColor: colors.blueBackground, alignItems: 'center', justifyContent: 'center' },
  analysisTitle: { color: colors.text, fontSize: 15, fontWeight: '900' },
  analysisText: { color: colors.textSecondary, fontSize: 11, lineHeight: 17, marginTop: 4 },
  empty: { flex: 1, padding: spacing.xl, justifyContent: 'center', gap: spacing.xl },
  primaryAction: { minHeight: 48, borderRadius: 14, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  primaryActionText: { color: colors.onPrimary, fontWeight: '900' }
});
