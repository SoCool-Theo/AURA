import React from 'react';
import { ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { PageTitle } from '../../components/ui/PageTitle';
import { colors, spacing } from '../../theme/theme';

export function WatchlistScreen() {
  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content}>
        <PageTitle title="Watchlist" subtitle="Coming later" />
        <Card><EmptyState icon="eye-outline" title="Watchlist is unavailable" description="Aura does not yet support saved watchlists or live market quotes. No prices or watchlist entries are loaded or saved here." /></Card>
      </ScrollView>
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 110, gap: spacing.xl }
});
