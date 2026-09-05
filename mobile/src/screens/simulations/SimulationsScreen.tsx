import React, { useCallback } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';

import { Card } from '../../components/ui/Card';
import { PageTitle } from '../../components/ui/PageTitle';
import { SectionHeader } from '../../components/ui/SectionHeader';
import { Tag } from '../../components/ui/Tag';
import { usePortfolios } from '../../portfolio/usePortfolios';
import { simulationErrorMessage } from '../../simulation/simulationErrors';
import { formatSimulationTimestamp, simulationTypeLabel } from '../../simulation/simulationFormatting';
import { useSimulations } from '../../simulation/useSimulations';
import { colors, spacing } from '../../theme/theme';

const modes = [
  { title: 'Historical Scenario', subtitle: 'Run your saved portfolio through a backend-defined market event.', icon: 'time-outline' as const, bg: colors.purpleBackground, fg: colors.purpleSoft, route: 'HistoricalScenario' },
  { title: 'Allocation Change', subtitle: 'Compare original and modified weights over an explicit period.', icon: 'pie-chart-outline' as const, bg: colors.cyanBackground, fg: colors.primary, route: 'AllocationChange' },
  { title: 'Combined Simulation', subtitle: 'Compare both allocations during the same historical event.', icon: 'git-compare-outline' as const, bg: colors.blueBackground, fg: colors.blue, route: 'CombinedSimulation' }
] as const;

export function SimulationsScreen({ navigation }: { navigation: any }) {
  const { portfolios, activePortfolioId, listStatus } = usePortfolios();
  const { history, historyStatus, historyError, refreshHistory } = useSimulations();

  useFocusEffect(useCallback(() => {
    if (listStatus === 'ready' || portfolios.length) void refreshHistory(portfolios);
  }, [listStatus, portfolios, refreshHistory]));

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content}>
        <PageTitle title="Simulations" subtitle="Backend-powered what-if analysis for historical events and portfolio allocations." />

        <View style={styles.modeList}>
          {modes.map((mode) => (
            <Pressable key={mode.title} onPress={() => navigation.navigate(mode.route, { portfolioId: activePortfolioId ?? undefined })}>
              <Card style={[styles.modeCard, { borderColor: mode.bg }]}>
                <View style={[styles.modeIcon, { backgroundColor: mode.bg }]}><Ionicons name={mode.icon} color={mode.fg} size={27} /></View>
                <View style={{ flex: 1 }}><Text style={styles.modeTitle}>{mode.title}</Text><Text style={styles.modeText}>{mode.subtitle}</Text></View>
                <Ionicons name="arrow-forward" color={mode.fg} size={19} />
              </Card>
            </Pressable>
          ))}
        </View>

        <SectionHeader title="Recent simulations" action="View all" onPress={() => navigation.navigate('SimulationHistory')} />

        {historyStatus === 'error' ? (
          <Card style={styles.errorCard}>
            <Text style={styles.errorTitle}>Complete history unavailable</Text>
            <Text style={styles.errorText}>{simulationErrorMessage(historyError, 'At least one portfolio history request failed. Retry from Simulation History.')}</Text>
          </Card>
        ) : historyStatus === 'loading' || historyStatus === 'idle' ? (
          <Text style={styles.loading}>Loading backend history…</Text>
        ) : history.length ? (
          <View style={styles.recentList}>
            {history.slice(0, 3).map((item) => (
              <Pressable key={item.id} onPress={() => navigation.navigate('SimulationResult', { portfolioId: item.portfolio_id, simulationId: item.id })}>
                <Card style={styles.recentCard}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.recentPortfolio}>{item.portfolio_name}</Text>
                    <Text style={styles.recentPeriod}>{item.requested_start_date} → {item.requested_end_date}</Text>
                    <Text style={styles.recentDate}>{formatSimulationTimestamp(item.created_at)}</Text>
                  </View>
                  <Tag label={simulationTypeLabel(item.simulation_type)} tone="primary" />
                </Card>
              </Pressable>
            ))}
          </View>
        ) : (
          <Card style={styles.emptyCard}>
            <Ionicons name="pulse-outline" color={colors.muted} size={28} />
            <Text style={styles.emptyTitle}>No simulation history yet</Text>
            <Text style={styles.emptyText}>Run one of the three backend simulation modes above.</Text>
          </Card>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 108 },
  modeList: { gap: spacing.md, marginTop: spacing.xl },
  modeCard: { minHeight: 112, flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  modeIcon: { width: 62, height: 62, borderRadius: 18, alignItems: 'center', justifyContent: 'center' },
  modeTitle: { color: colors.text, fontSize: 17, fontWeight: '900' },
  modeText: { color: colors.textSecondary, fontSize: 12, lineHeight: 18, marginTop: 5 },
  recentList: { gap: spacing.md },
  recentCard: { flexDirection: 'row', gap: spacing.md, alignItems: 'center' },
  recentPortfolio: { color: colors.text, fontWeight: '900' },
  recentPeriod: { color: colors.textSecondary, fontSize: 10, marginTop: 4 },
  recentDate: { color: colors.muted, fontSize: 9, marginTop: 4 },
  emptyCard: { alignItems: 'center', gap: spacing.sm, paddingVertical: spacing.xxl },
  emptyTitle: { color: colors.text, fontWeight: '900' },
  emptyText: { color: colors.muted, textAlign: 'center', fontSize: 12 },
  loading: { color: colors.textSecondary },
  errorCard: { gap: spacing.sm, borderColor: colors.dangerBorder },
  errorTitle: { color: colors.danger, fontWeight: '900' },
  errorText: { color: colors.textSecondary, fontSize: 11, lineHeight: 17 }
});
