import React from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Card } from '../../components/ui/Card';
import { PageTitle } from '../../components/ui/PageTitle';
import { SectionHeader } from '../../components/ui/SectionHeader';
import { Tag } from '../../components/ui/Tag';
import { RiskDriverCard } from '../../components/portfolio/RiskDriverCard';
import { useAppData } from '../../hooks/useAppData';
import { colors, spacing } from '../../theme/theme';
import { formatPercent } from '../../utils/formatting';

export function ReportDetailScreen({ route }: { route: any }) {
  const { reports } = useAppData();
  const report = reports.find((item) => item.id === route.params.reportId);

  if (!report) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.empty}><Text style={styles.emptyText}>Report not found.</Text></View>
      </SafeAreaView>
    );
  }

  const analysis = report.analysis;

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content}>
        <PageTitle
          title="Report Detail"
          subtitle={new Date(report.createdAt).toLocaleString()}
          right={
            <View style={styles.share}>
              <Ionicons name="share-outline" color={colors.textSecondary} size={20} />
            </View>
          }
        />

        <Card style={styles.reportHeader}>
          <View style={styles.reportIcon}>
            <Ionicons name="document-text-outline" color={colors.purpleSoft} size={23} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.reportTitle}>{report.portfolioName} Analysis</Text>
            <Text style={styles.reportType}>Analysis Report</Text>
          </View>
          <Ionicons name="chevron-forward" color={colors.muted} size={18} />
        </Card>

        <Card style={styles.summaryCard}>
          <Text style={styles.overline}>SUMMARY</Text>
          <Text style={styles.summary}>
            Your portfolio currently shows {analysis.riskLevel.toLowerCase()} with risk driven by concentration, volatility and diversification signals.
          </Text>
        </Card>

        <SectionHeader title="Key metrics" />
        <View style={styles.grid}>
          <Card style={styles.metric}>
            <Text style={styles.metricLabel}>Risk score</Text>
            <Text style={styles.metricValue}>{analysis.riskScore}/100</Text>
            <Tag label={analysis.riskLevel} tone="warning" />
          </Card>
          <Card style={styles.metric}>
            <Text style={styles.metricLabel}>Volatility</Text>
            <Text style={styles.metricValue}>{formatPercent(analysis.volatility)}</Text>
            <Tag label="High" tone="danger" />
          </Card>
          <Card style={styles.metric}>
            <Text style={styles.metricLabel}>Sharpe ratio</Text>
            <Text style={styles.metricValue}>{analysis.sharpeRatio.toFixed(2)}</Text>
            <Tag label="Fair" tone="warning" />
          </Card>
          <Card style={styles.metric}>
            <Text style={styles.metricLabel}>Max drawdown</Text>
            <Text style={styles.metricValue}>{formatPercent(analysis.maxDrawdown)}</Text>
            <Tag label="High" tone="danger" />
          </Card>
        </View>

        <SectionHeader title="Risk drivers" />
        <View style={styles.list}>
          {analysis.topRiskDrivers.map((driver) => (
            <RiskDriverCard key={driver.symbol} driver={driver} />
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 100 },
  share: { width: 40, height: 40, borderRadius: 13, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, alignItems: 'center', justifyContent: 'center' },
  reportHeader: { marginTop: spacing.xl, flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  reportIcon: { width: 48, height: 48, borderRadius: 15, backgroundColor: colors.purpleBackground, alignItems: 'center', justifyContent: 'center' },
  reportTitle: { color: colors.text, fontSize: 15, fontWeight: '900' },
  reportType: { color: colors.muted, fontSize: 10, marginTop: 4 },
  summaryCard: { marginTop: spacing.md, gap: spacing.sm },
  overline: { color: colors.muted, fontSize: 9, fontWeight: '900', letterSpacing: 1 },
  summary: { color: colors.textSecondary, lineHeight: 20, fontSize: 13 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  metric: { width: '47.8%', gap: spacing.sm },
  metricLabel: { color: colors.muted, fontSize: 10, fontWeight: '800' },
  metricValue: { color: colors.text, fontSize: 19, fontWeight: '900' },
  list: { gap: spacing.md },
  empty: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  emptyText: { color: colors.textSecondary }
});
