import React, { useCallback, useMemo, useState } from 'react';
import { Pressable, RefreshControl, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';

import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { LoadingState } from '../../components/ui/LoadingState';
import { Tag } from '../../components/ui/Tag';
import { portfolioErrorMessage } from '../../portfolio/portfolioErrors';
import { usePortfolios } from '../../portfolio/usePortfolios';
import { simulationErrorMessage } from '../../simulation/simulationErrors';
import { formatSimulationTimestamp, simulationTypeLabel } from '../../simulation/simulationFormatting';
import { useSimulations } from '../../simulation/useSimulations';
import { colors, spacing, typography } from '../../theme/theme';

export function SimulationHistoryScreen({ navigation }: { navigation: any }) {
  const { portfolios, listStatus, listError, refreshPortfolios } = usePortfolios();
  const { history, historyStatus, historyError, isRefreshingHistory, refreshHistory } = useSimulations();
  const [query, setQuery] = useState('');
  const [portfolioFilter, setPortfolioFilter] = useState('');

  useFocusEffect(useCallback(() => {
    if (listStatus === 'ready' || portfolios.length) void refreshHistory(portfolios);
  }, [listStatus, portfolios, refreshHistory]));

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return history.filter((item) => (
      (!portfolioFilter || item.portfolio_id === portfolioFilter)
      && (!normalized || item.portfolio_name.toLowerCase().includes(normalized) || item.id.toLowerCase().includes(normalized))
    ));
  }, [history, portfolioFilter, query]);

  function retry() {
    if (listStatus === 'error' && !portfolios.length) void refreshPortfolios();
    else void refreshHistory(portfolios);
  }

  if (((listStatus === 'idle' || listStatus === 'loading') && !portfolios.length)
    || ((historyStatus === 'idle' || historyStatus === 'loading') && !history.length && listStatus !== 'error')) {
    return <LoadingState message="Loading simulation history…" />;
  }

  const blockingError = listStatus === 'error' && !portfolios.length
    ? portfolioErrorMessage(listError)
    : historyStatus === 'error' && !history.length
      ? simulationErrorMessage(historyError, 'Unable to load complete simulation history.')
      : null;

  if (blockingError) {
    return (
      <SafeAreaView style={styles.safe} edges={['bottom']}>
        <View style={styles.center}><Card style={styles.errorCard}>
          <Text style={styles.errorTitle}>Simulation history unavailable</Text>
          <Text style={styles.errorText}>{blockingError}</Text>
          <Button title="Retry" onPress={retry} />
        </Card></View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        refreshControl={<RefreshControl refreshing={isRefreshingHistory} onRefresh={() => void refreshHistory(portfolios)} tintColor={colors.primary} />}
      >
        <Text style={styles.title}>Simulation History</Text>
        <Text style={styles.subtitle}>Immutable simulation runs stored by Aura's backend, newest first.</Text>

        {historyStatus === 'error' && history.length ? (
          <Card style={styles.errorCard}>
            <Text style={styles.errorTitle}>Could not refresh complete history</Text>
            <Text style={styles.errorText}>{simulationErrorMessage(historyError, 'At least one portfolio history request failed. The prior complete list remains visible.')}</Text>
            <Button title="Retry" onPress={retry} />
          </Card>
        ) : null}

        {history.length ? (
          <>
            <View style={styles.search}>
              <Ionicons name="search-outline" color={colors.muted} size={17} />
              <TextInput value={query} onChangeText={setQuery} placeholder="Search portfolio name or simulation ID" placeholderTextColor={colors.muted} style={styles.searchInput} />
            </View>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filters}>
              <Pressable onPress={() => setPortfolioFilter('')}><Tag label="All portfolios" tone={!portfolioFilter ? 'primary' : 'default'} /></Pressable>
              {portfolios.map((portfolio) => <Pressable key={portfolio.id} onPress={() => setPortfolioFilter(portfolio.id)}><Tag label={portfolio.name} tone={portfolioFilter === portfolio.id ? 'primary' : 'default'} /></Pressable>)}
            </ScrollView>
          </>
        ) : null}

        <View style={styles.list}>
          {!history.length ? (
            <Card><EmptyState icon="pulse-outline" title="No simulations yet" description="Run a historical, allocation, or combined simulation to create backend history." /></Card>
          ) : filtered.length ? filtered.map((item) => (
            <Pressable key={item.id} onPress={() => navigation.navigate('SimulationResult', { portfolioId: item.portfolio_id, simulationId: item.id })}>
              <Card style={styles.card}>
                <View style={styles.icon}><Ionicons name="pulse-outline" color={colors.primary} size={22} /></View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.name}>{item.portfolio_name}</Text>
                  <Text style={styles.mode}>{simulationTypeLabel(item.simulation_type)}</Text>
                  <Text style={styles.period}>{item.requested_start_date} → {item.requested_end_date}</Text>
                  <Text style={styles.date}>{formatSimulationTimestamp(item.created_at)}</Text>
                  <Text style={styles.id}>ID · {item.id}</Text>
                </View>
                <Ionicons name="chevron-forward" color={colors.muted} size={18} />
              </Card>
            </Pressable>
          )) : (
            <Card><EmptyState icon="search-outline" title="No matching simulations" description="Change the portfolio filter or search text." /></Card>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 100 },
  title: { color: colors.text, ...typography.h1 },
  subtitle: { color: colors.textSecondary, marginTop: 6, marginBottom: spacing.xl },
  search: { height: 44, borderRadius: 13, backgroundColor: colors.surfaceAlt, borderWidth: 1, borderColor: colors.borderSoft, flexDirection: 'row', alignItems: 'center', gap: spacing.sm, paddingHorizontal: spacing.md },
  searchInput: { flex: 1, color: colors.text, fontSize: 12 },
  filters: { gap: spacing.sm, paddingVertical: spacing.lg },
  list: { gap: spacing.md },
  card: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  icon: { width: 48, height: 48, borderRadius: 15, backgroundColor: colors.cyanBackground, alignItems: 'center', justifyContent: 'center' },
  name: { color: colors.text, fontSize: 14, fontWeight: '900' },
  mode: { color: colors.primary, fontSize: 11, fontWeight: '800', marginTop: 3 },
  period: { color: colors.textSecondary, fontSize: 10, marginTop: 4 },
  date: { color: colors.muted, fontSize: 9, marginTop: 4 },
  id: { color: colors.muted, fontSize: 8, marginTop: 3 },
  center: { flex: 1, justifyContent: 'center', padding: spacing.xl },
  errorCard: { gap: spacing.md, borderColor: colors.dangerBorder, marginBottom: spacing.lg },
  errorTitle: { color: colors.danger, fontSize: 15, fontWeight: '900' },
  errorText: { color: colors.textSecondary, fontSize: 12, lineHeight: 18 }
});
