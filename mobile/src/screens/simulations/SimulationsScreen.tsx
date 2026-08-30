import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Card } from '../../components/ui/Card';
import { PageTitle } from '../../components/ui/PageTitle';
import { SectionHeader } from '../../components/ui/SectionHeader';
import { Tag } from '../../components/ui/Tag';
import { useAppData } from '../../hooks/useAppData';
import { colors, spacing } from '../../theme/theme';
import { formatPercent } from '../../utils/formatting';

const modes = [
  {
    title: 'Historical Scenario',
    subtitle: 'See how your current portfolio behaves during a selected past event.',
    icon: 'time-outline' as const,
    bg: colors.purpleBackground,
    fg: colors.purpleSoft,
    route: 'HistoricalScenario'
  },
  {
    title: 'Allocation Change',
    subtitle: 'See how changing allocations could affect demo risk and return.',
    icon: 'pie-chart-outline' as const,
    bg: colors.cyanBackground,
    fg: colors.primary,
    route: 'AllocationChange'
  },
  {
    title: 'Combined Simulation',
    subtitle: 'Compare original vs. changed allocations during the same event.',
    icon: 'git-compare-outline' as const,
    bg: colors.blueBackground,
    fg: colors.blue,
    route: 'CombinedSimulation'
  }
] as const;

export function SimulationsScreen({ navigation }: { navigation: any }) {
  const { activePortfolio, simulations } = useAppData();

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content}>
        <PageTitle
          title="Simulations"
          subtitle="What-If analysis for historical events and portfolio allocations."
        />

        <View style={styles.modeList}>
          {modes.map((mode) => (
            <Pressable
              key={mode.title}
              onPress={() => navigation.navigate(mode.route, { portfolioId: activePortfolio?.id })}
            >
              <Card style={[styles.modeCard, { borderColor: mode.bg }]}>
                <View style={[styles.modeIcon, { backgroundColor: mode.bg }]}>
                  <Ionicons name={mode.icon} color={mode.fg} size={27} />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.modeTitle}>{mode.title}</Text>
                  <Text style={styles.modeText}>{mode.subtitle}</Text>
                </View>
                <Ionicons name="arrow-forward" color={mode.fg} size={19} />
              </Card>
            </Pressable>
          ))}
        </View>

        <SectionHeader
          title="Recent simulations"
          action="View all"
          onPress={() => navigation.navigate('SimulationHistory')}
        />

        {simulations.length ? (
          <View style={styles.recentList}>
            {simulations.slice(0, 3).map((record) => (
              <Pressable
                key={record.id}
                onPress={() => navigation.navigate('SimulationResult', { simulationId: record.id })}
              >
                <Card style={styles.recentCard}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.recentPortfolio}>{record.portfolioName}</Text>
                    <Text style={styles.recentTitle}>{record.title}</Text>
                    <Text style={styles.recentDate}>{new Date(record.createdAt).toLocaleDateString()}</Text>
                  </View>
                  <View style={styles.recentRight}>
                    <Text style={[styles.recentReturn, { color: record.original.cumulativeReturn < 0 ? colors.danger : colors.success }]}>
                      {formatPercent(record.original.cumulativeReturn)}
                    </Text>
                    <Tag label={record.mode} tone="primary" />
                  </View>
                </Card>
              </Pressable>
            ))}
          </View>
        ) : (
          <Card style={styles.emptyCard}>
            <Ionicons name="pulse-outline" color={colors.muted} size={28} />
            <Text style={styles.emptyTitle}>No simulation history yet</Text>
            <Text style={styles.emptyText}>Run one of the three simulation modes above.</Text>
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
  recentTitle: { color: colors.textSecondary, fontSize: 12, marginTop: 4 },
  recentDate: { color: colors.muted, fontSize: 10, marginTop: 4 },
  recentRight: { alignItems: 'flex-end', gap: spacing.sm },
  recentReturn: { fontSize: 15, fontWeight: '900' },
  emptyCard: { alignItems: 'center', gap: spacing.sm, paddingVertical: spacing.xxl },
  emptyTitle: { color: colors.text, fontWeight: '900' },
  emptyText: { color: colors.muted, textAlign: 'center', fontSize: 12 }
});
