import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Card } from '../../components/ui/Card';
import { PageTitle } from '../../components/ui/PageTitle';
import { useAppData } from '../../hooks/useAppData';
import { colors, spacing } from '../../theme/theme';

const items = [
  { label: 'Analytics', description: 'Detailed risk metrics', icon: 'analytics-outline', color: colors.primary, bg: colors.cyanBackground, route: 'Analytics' },
  { label: 'Reports', description: 'Saved analysis snapshots', icon: 'document-text-outline', color: colors.purpleSoft, bg: colors.purpleBackground, route: 'Reports' },
  { label: 'Watchlist', description: 'Track selected market assets', icon: 'eye-outline', color: colors.warning, bg: colors.warningBackground, route: 'Watchlist' },
  { label: 'Learn', description: 'Portfolio-risk education', icon: 'school-outline', color: colors.blue, bg: colors.blueBackground, route: 'Learn' },
  { label: 'Settings', description: 'Account and preferences', icon: 'settings-outline', color: colors.textSecondary, bg: colors.surfaceAlt, route: 'Settings' }
] as const;

export function MoreScreen({ navigation }: { navigation: any }) {
  const { reports, simulations, watchlistSymbols, activePortfolio } = useAppData();

  function open(route: (typeof items)[number]['route']) {
    if (route === 'Analytics') {
      navigation.navigate('Analytics', { portfolioId: activePortfolio?.id });
      return;
    }
    navigation.navigate(route);
  }

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content}>
        <PageTitle title="More" subtitle="Reports, learning, watchlist and settings." />

        <View style={styles.summaryRow}>
          <Card style={styles.summaryCard}>
            <Text style={styles.summaryValue}>{reports.length}</Text>
            <Text style={styles.summaryLabel}>Reports</Text>
          </Card>
          <Card style={styles.summaryCard}>
            <Text style={styles.summaryValue}>{simulations.length}</Text>
            <Text style={styles.summaryLabel}>Simulations</Text>
          </Card>
          <Card style={styles.summaryCard}>
            <Text style={styles.summaryValue}>{watchlistSymbols.length}</Text>
            <Text style={styles.summaryLabel}>Watching</Text>
          </Card>
        </View>

        <View style={styles.list}>
          {items.map((item) => (
            <Pressable key={item.label} onPress={() => open(item.route)}>
              <Card style={styles.item}>
                <View style={[styles.icon, { backgroundColor: item.bg }]}>
                  <Ionicons name={item.icon} color={item.color} size={22} />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.label}>{item.label}</Text>
                  <Text style={styles.description}>{item.description}</Text>
                </View>
                <Ionicons name="chevron-forward" color={colors.muted} size={19} />
              </Card>
            </Pressable>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 108 },
  summaryRow: { flexDirection: 'row', gap: spacing.sm, marginTop: spacing.xl },
  summaryCard: { flex: 1, alignItems: 'center', paddingHorizontal: spacing.sm },
  summaryValue: { color: colors.text, fontSize: 20, fontWeight: '900' },
  summaryLabel: { color: colors.muted, fontSize: 9, marginTop: 3 },
  list: { gap: spacing.md, marginTop: spacing.xl },
  item: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  icon: { width: 48, height: 48, borderRadius: 15, alignItems: 'center', justifyContent: 'center' },
  label: { color: colors.text, fontSize: 15, fontWeight: '900' },
  description: { color: colors.muted, fontSize: 11, marginTop: 4 }
});
