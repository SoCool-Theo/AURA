import React from 'react';
import { ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { PageTitle } from '../../components/ui/PageTitle';
import { colors, spacing } from '../../theme/theme';

export function AssistantScreen() {
  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content}>
        <PageTitle title="AI Assistant" subtitle="Coming later" />
        <Card><EmptyState icon="sparkles-outline" title="AI explanations are unavailable" description="Aura's AI integration is not available yet. Use Analytics, saved Reports, and Simulations to explore your portfolio results." /></Card>
      </ScrollView>
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 110, gap: spacing.xl }
});
