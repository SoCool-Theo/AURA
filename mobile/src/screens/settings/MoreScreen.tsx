import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Card } from '../../components/ui/Card';
import { InlineErrorCard } from '../../components/ui/ErrorState';
import { PageTitle } from '../../components/ui/PageTitle';
import { usePortfolios } from '../../portfolio/usePortfolios';
import { useReports } from '../../report/useReports';
import { useSimulations } from '../../simulation/useSimulations';
import { colors, spacing } from '../../theme/theme';
import { useFocusEffect } from '@react-navigation/native';
import { useNotificationBadge } from '../../notifications/useNotifications';

const items = [
  { label: 'Analytics', description: 'Detailed risk metrics', icon: 'analytics-outline', color: colors.primary, bg: colors.cyanBackground, route: 'Analytics' },
  { label: 'Forecasting', description: '7–30-day portfolio and asset outlooks · weekly experimental', icon: 'trending-up-outline', color: colors.primary, bg: colors.cyanBackground, route: 'Forecasting' },
  { label: 'Reports', description: 'Saved analysis results', icon: 'document-text-outline', color: colors.purpleSoft, bg: colors.purpleBackground, route: 'Reports' },
  { label: 'Watchlist', description: 'Follow supported assets', icon: 'eye-outline', color: colors.primary, bg: colors.cyanBackground, route: 'Watchlist' },
  { label: 'Learn', description: 'Portfolio-risk education', icon: 'school-outline', color: colors.blue, bg: colors.blueBackground, route: 'Learn' },
  { label: 'Notifications', description: 'Saved analysis and simulation updates', icon: 'notifications-outline', color: colors.primary, bg: colors.cyanBackground, route: 'Notifications' },
  { label: 'Settings', description: 'Account and preferences', icon: 'settings-outline', color: colors.textSecondary, bg: colors.surfaceAlt, route: 'Settings' }
] as const;

export function MoreScreen({ navigation }: { navigation: any }) {
  const unread = useNotificationBadge();
  const {
    portfolios,
    activePortfolioId,
    listStatus,
    listError,
    refreshPortfolios
  } = usePortfolios();
  const {
    reports,
    historyStatus,
    historyError,
    refreshReportHistory
  } = useReports();
  const {
    history: simulations,
    historyStatus: simulationHistoryStatus,
    historyError: simulationHistoryError,
    refreshHistory: refreshSimulationHistory
  } = useSimulations();

  useFocusEffect(React.useCallback(() => {
    if (listStatus === 'ready' || portfolios.length) {
      void refreshReportHistory(portfolios);
      void refreshSimulationHistory(portfolios);
    }
  }, [listStatus, portfolios, refreshReportHistory, refreshSimulationHistory]));

  function open(route: (typeof items)[number]['route']) {
    if (route === 'Forecasting') {
      navigation.navigate('Forecasting', { portfolioId: activePortfolioId ?? undefined, returnToHome: false });
      return;
    }
    if (route === 'Analytics') {
      navigation.navigate('Analytics', {
        portfolioId: activePortfolioId ?? undefined
      });
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
            <Text style={styles.summaryValue}>
              {listStatus === 'ready' && historyStatus === 'ready' ? reports.length : '—'}
            </Text>
            <Text style={styles.summaryLabel}>Reports</Text>
          </Card>
          <Card style={styles.summaryCard}>
            <Text style={styles.summaryValue}>
              {listStatus === 'ready' && simulationHistoryStatus === 'ready' ? simulations.length : '—'}
            </Text>
            <Text style={styles.summaryLabel}>Simulations</Text>
          </Card>
        </View>

        {listStatus === 'error' ? (
          <InlineErrorCard
            error={listError}
            stale={Boolean(portfolios.length)}
            onRetry={() => void refreshPortfolios()}
            retryTitle="Retry portfolios"
          />
        ) : null}
        {historyStatus === 'error' ? (
          <InlineErrorCard
            error={historyError}
            stale={Boolean(reports.length)}
            onRetry={() => void refreshReportHistory(portfolios)}
            retryTitle="Retry reports"
          />
        ) : null}
        {simulationHistoryStatus === 'error' ? (
          <InlineErrorCard
            error={simulationHistoryError}
            stale={Boolean(simulations.length)}
            onRetry={() => void refreshSimulationHistory(portfolios)}
            retryTitle="Retry simulations"
          />
        ) : null}

        <View style={styles.list}>
          {items.map((item) => (
            <Pressable
              accessibilityLabel={item.route === 'Notifications' && unread != null ? `Notifications, ${unread} unread` : item.label}
              accessibilityRole="button"
              key={item.label}
              onPress={() => open(item.route)}
            >
              <Card style={styles.item}>
                <View style={[styles.icon, { backgroundColor: item.bg }]}>
                  <Ionicons name={item.icon} color={item.color} size={22} />
                  {item.route === 'Notifications' && unread != null && unread > 0 && <View accessible={false} style={styles.notificationDot} />}
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.label}>{item.label}</Text>
                  {item.route === 'Notifications' && unread != null && unread > 0 && <Text style={{ color: colors.primary, fontWeight: '800', fontSize: 12 }}>{unread} unread</Text>}
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
  notificationDot: { position: 'absolute', top: 9, right: 9, width: 9, height: 9, borderRadius: 5, backgroundColor: colors.danger, borderWidth: 1, borderColor: colors.surface },
  label: { color: colors.text, fontSize: 15, fontWeight: '900' },
  description: { color: colors.muted, fontSize: 11, marginTop: 4 }
});
