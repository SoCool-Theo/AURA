import React from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { MetricCard } from '../../components/portfolio/MetricCard';
import { useAppData } from '../../hooks/useAppData';
import { colors, spacing, typography } from '../../theme/theme';
import { formatCurrency, formatPercent } from '../../utils/formatting';

export function SimulationResultScreen({ route }: { route: any }) {
  const { simulations } = useAppData();
  const record = simulations.find((item) => item.id === route.params.simulationId);

  if (!record) {
    return <SafeAreaView style={styles.safe}><EmptyState title="Simulation not found" description="Open Simulation History and choose another result." /></SafeAreaView>;
  }

  const original = record.original;
  const modified = record.modified;

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.eyebrow}>{record.mode.toUpperCase()}</Text>
        <Text style={styles.title}>{record.title}</Text>
        <Text style={styles.subtitle}>{record.portfolioName} · saved locally</Text>

        <Card style={styles.hero}>
          <Text style={styles.heroLabel}>ORIGINAL PORTFOLIO RETURN</Text>
          <Text style={[styles.heroValue, { color: original.cumulativeReturn < 0 ? colors.danger : colors.success }]}>
            {formatPercent(original.cumulativeReturn)}
          </Text>
          <Text style={styles.heroCaption}>Demo result for frontend interaction only</Text>
        </Card>

        <View style={styles.grid}>
          <MetricCard label="Ending Value" value={formatCurrency(original.endingValue)} />
          <MetricCard label="Volatility" value={formatPercent(original.annualizedVolatility)} />
          <MetricCard label="Max Drawdown" value={formatPercent(original.maxDrawdown)} />
          <MetricCard label="Sharpe Ratio" value={original.sharpeRatio?.toFixed(2) ?? '—'} />
        </View>

        {modified ? (
          <>
            <Text style={styles.section}>Modified allocation</Text>
            <Card style={styles.compareCard}>
              <View style={styles.compareRow}>
                <Text style={styles.compareLabel}>Return</Text>
                <Text style={styles.compareValue}>{formatPercent(modified.cumulativeReturn)}</Text>
              </View>
              <View style={styles.compareRow}>
                <Text style={styles.compareLabel}>Ending value</Text>
                <Text style={styles.compareValue}>{formatCurrency(modified.endingValue)}</Text>
              </View>
              <View style={styles.compareRow}>
                <Text style={styles.compareLabel}>Volatility</Text>
                <Text style={styles.compareValue}>{formatPercent(modified.annualizedVolatility)}</Text>
              </View>
              <View style={styles.compareRow}>
                <Text style={styles.compareLabel}>Max drawdown</Text>
                <Text style={styles.compareValue}>{formatPercent(modified.maxDrawdown)}</Text>
              </View>
            </Card>

            {record.comparison ? (
              <>
                <Text style={styles.section}>Difference</Text>
                <Card style={styles.deltaCard}>
                  <Text style={styles.deltaText}>
                    Return delta: {formatPercent(record.comparison.returnDelta)}
                  </Text>
                  <Text style={styles.deltaText}>
                    Volatility delta: {formatPercent(record.comparison.volatilityDelta)}
                  </Text>
                  <Text style={styles.deltaText}>
                    Drawdown delta: {formatPercent(record.comparison.drawdownDelta)}
                  </Text>
                </Card>
              </>
            ) : null}
          </>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 100 },
  eyebrow: { color: colors.primary, fontSize: 10, fontWeight: '900', letterSpacing: 1.3 },
  title: { color: colors.text, ...typography.h1, marginTop: 4 },
  subtitle: { color: colors.textSecondary, marginTop: 6, marginBottom: spacing.xl },
  hero: { alignItems: 'center', gap: spacing.sm },
  heroLabel: { color: colors.muted, fontSize: 10, fontWeight: '900', letterSpacing: 1.1 },
  heroValue: { fontSize: 44, fontWeight: '900' },
  heroCaption: { color: colors.textSecondary, fontSize: 12 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', gap: spacing.md, marginVertical: spacing.xl },
  section: { color: colors.text, ...typography.h2, marginTop: spacing.xl, marginBottom: spacing.md },
  compareCard: { gap: spacing.md },
  compareRow: { flexDirection: 'row', justifyContent: 'space-between' },
  compareLabel: { color: colors.textSecondary },
  compareValue: { color: colors.text, fontWeight: '900' },
  deltaCard: { gap: spacing.sm },
  deltaText: { color: colors.textSecondary, fontWeight: '700' }
});
