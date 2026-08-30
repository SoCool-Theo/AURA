import React from 'react';
import { Alert, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { PageTitle } from '../../components/ui/PageTitle';
import { SectionHeader } from '../../components/ui/SectionHeader';
import { Tag } from '../../components/ui/Tag';

import { RiskGauge } from '../../components/charts/RiskGauge';
import { AssetRelationshipBars } from '../../components/charts/AssetRelationshipBars';
import { RiskDriverCard } from '../../components/portfolio/RiskDriverCard';

import { useAppData } from '../../hooks/useAppData';
import { demoAnalyzePortfolio } from '../../utils/localCalculations';

import { colors, spacing } from '../../theme/theme';
import { formatPercent } from '../../utils/formatting';

export function PortfolioAnalysisScreen({ route }: { route: any }) {
  const { portfolios, activePortfolio, saveAnalysisReport } = useAppData();
  const portfolioId = route.params?.portfolioId ?? activePortfolio?.id;
  const portfolio = portfolios.find((item) => item.id === portfolioId);

  if (!portfolio) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.empty}>
          <Text style={styles.emptyText}>Select a portfolio to view analytics.</Text>
        </View>
      </SafeAreaView>
    );
  }

  const selectedPortfolio = portfolio;
  const analysis = demoAnalyzePortfolio(selectedPortfolio);

  async function saveReport() {
    const report = await saveAnalysisReport(selectedPortfolio.id);
    if (report) {
      Alert.alert(
        'Report saved',
        'This local analysis snapshot is now available in Reports.'
      );
    }
  }

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content}>
        <PageTitle
          eyebrow="PORTFOLIO ANALYSIS"
          title={selectedPortfolio.name}
          subtitle="Understand the main signals behind your portfolio risk."
        />

        <Card style={styles.riskSummary}>
          <View style={styles.gaugeColumn}>
            <Text style={styles.overline}>OVERALL RISK</Text>
            <RiskGauge score={analysis.riskScore} size={126} strokeWidth={10} />
            <Tag
              label={analysis.riskLevel}
              tone={
                analysis.riskScore >= 70
                  ? 'danger'
                  : analysis.riskScore >= 40
                    ? 'warning'
                    : 'success'
              }
            />
          </View>

          <View style={styles.summaryDivider} />

          <View style={styles.summaryMetrics}>
            <View style={styles.metricRow}>
              <Text style={styles.metricLabel}>Volatility</Text>
              <Text style={styles.metricValue}>{formatPercent(analysis.volatility)}</Text>
            </View>

            <View style={styles.metricRow}>
              <Text style={styles.metricLabel}>Sharpe ratio</Text>
              <Text style={styles.metricValue}>{analysis.sharpeRatio.toFixed(2)}</Text>
            </View>

            <View style={styles.metricRow}>
              <Text style={styles.metricLabel}>Max drawdown</Text>
              <Text style={[styles.metricValue, { color: colors.danger }]}>
                {formatPercent(analysis.maxDrawdown)}
              </Text>
            </View>

            <View style={styles.metricRow}>
              <Text style={styles.metricLabel}>Diversification</Text>
              <Text style={styles.metricValue}>{analysis.diversification}</Text>
            </View>
          </View>
        </Card>

        <SectionHeader title="Main risk drivers" />

        <View style={styles.driverList}>
          {analysis.topRiskDrivers.map((driver) => (
            <RiskDriverCard key={driver.symbol} driver={driver} />
          ))}
        </View>

        <SectionHeader title="Asset relationships" />

        <Card style={styles.relationshipCard}>
          <View style={styles.relationshipHeader}>
            <View>
              <Text style={styles.relationshipTitle}>Correlation pairs</Text>
              <Text style={styles.relationshipSubtitle}>
                Easier to read on mobile than a heatmap.
              </Text>
            </View>
            <Tag label="DEMO" tone="primary" />
          </View>

          <AssetRelationshipBars holdings={selectedPortfolio.holdings} />
        </Card>

        <SectionHeader title="What this means" />

        <Card style={styles.explanationCard}>
          <Text style={styles.explanationTitle}>Diversification context</Text>
          <Text style={styles.explanationText}>
            Higher positive correlation means two assets have historically tended to move in the same direction. Lower or negative relationships can provide more diversification. Production values will be calculated from backend historical market data.
          </Text>
        </Card>

        <Button
          title="Save report snapshot"
          onPress={saveReport}
          style={{ marginTop: spacing.xl }}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.background
  },
  content: {
    padding: spacing.lg,
    paddingBottom: 100
  },
  riskSummary: {
    marginTop: spacing.xl,
    flexDirection: 'row',
    gap: spacing.lg,
    alignItems: 'stretch'
  },
  gaugeColumn: {
    width: 142,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm
  },
  overline: {
    color: colors.muted,
    fontSize: 9,
    fontWeight: '900',
    letterSpacing: 1
  },
  summaryDivider: {
    width: 1,
    backgroundColor: colors.borderSoft
  },
  summaryMetrics: {
    flex: 1,
    justifyContent: 'space-around'
  },
  metricRow: {
    gap: 3,
    paddingVertical: 5
  },
  metricLabel: {
    color: colors.muted,
    fontSize: 10,
    fontWeight: '700'
  },
  metricValue: {
    color: colors.text,
    fontSize: 15,
    fontWeight: '900'
  },
  driverList: {
    gap: spacing.md
  },
  relationshipCard: {
    gap: spacing.lg
  },
  relationshipHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: spacing.md
  },
  relationshipTitle: {
    color: colors.text,
    fontSize: 15,
    fontWeight: '900'
  },
  relationshipSubtitle: {
    color: colors.muted,
    fontSize: 10,
    marginTop: 4
  },
  explanationCard: {
    gap: spacing.sm
  },
  explanationTitle: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '900'
  },
  explanationText: {
    color: colors.textSecondary,
    fontSize: 12,
    lineHeight: 19
  },
  empty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center'
  },
  emptyText: {
    color: colors.textSecondary
  }
});
