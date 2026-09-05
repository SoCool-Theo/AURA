import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { SimulationResults } from '../../components/simulations/SimulationResults';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { LoadingState } from '../../components/ui/LoadingState';
import { simulationErrorMessage } from '../../simulation/simulationErrors';
import { formatSimulationTimestamp } from '../../simulation/simulationFormatting';
import type { SimulationRunResult } from '../../simulation/SimulationProvider';
import { useSimulations } from '../../simulation/useSimulations';
import type { SimulationHistoryDetailResponse } from '../../types/simulation';
import { colors, spacing, typography } from '../../theme/theme';

function toRunResult(detail: SimulationHistoryDetailResponse): SimulationRunResult {
  if (detail.simulation_type === 'historical-scenario') {
    return { type: 'historical-scenario', response: detail.result };
  }
  if (detail.simulation_type === 'allocation') {
    return { type: 'allocation', response: detail.result };
  }
  return { type: 'combined', response: detail.result };
}

export function SimulationResultScreen({ route }: { route: any }) {
  const { getHistoryDetail } = useSimulations();
  const { portfolioId, simulationId } = route.params;
  const [detail, setDetail] = useState<SimulationHistoryDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const requestRef = useRef(0);

  const load = useCallback(async () => {
    const requestId = requestRef.current + 1;
    requestRef.current = requestId;
    setLoading(true);
    setError(null);
    try {
      const response = await getHistoryDetail(portfolioId, simulationId);
      if (requestRef.current === requestId) setDetail(response);
    } catch (caught) {
      if (requestRef.current === requestId) setError(caught);
    } finally {
      if (requestRef.current === requestId) setLoading(false);
    }
  }, [getHistoryDetail, portfolioId, simulationId]);

  useEffect(() => {
    void load();
    return () => {
      requestRef.current += 1;
    };
  }, [load]);

  if (loading && !detail) return <LoadingState message="Loading saved simulation…" />;
  if (error && !detail) {
    return (
      <SafeAreaView style={styles.safe} edges={['bottom']}>
        <View style={styles.center}>
          <Card style={styles.errorCard}>
            <Text style={styles.errorTitle}>Simulation unavailable</Text>
            <Text style={styles.errorText}>{simulationErrorMessage(error, 'Unable to load this simulation result.')}</Text>
            <Button title="Retry" onPress={() => void load()} />
          </Card>
        </View>
      </SafeAreaView>
    );
  }
  if (!detail) return null;

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Saved Simulation</Text>
        <Text style={styles.subtitle}>Immutable backend history detail.</Text>
        <Card style={styles.metadata}>
          <Text style={styles.metaLabel}>SIMULATION ID</Text>
          <Text selectable style={styles.metaValue}>{detail.id}</Text>
          <Text style={styles.metaLabel}>PORTFOLIO ID</Text>
          <Text selectable style={styles.metaValue}>{detail.portfolio_id}</Text>
          <Text style={styles.metaLabel}>CREATED</Text>
          <Text style={styles.metaValue}>{formatSimulationTimestamp(detail.created_at)}</Text>
        </Card>
        {error ? <Text style={styles.refreshError}>Refresh failed; showing the previously loaded immutable result.</Text> : null}
        <SimulationResults result={toRunResult(detail)} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 100 },
  title: { color: colors.text, ...typography.h1 },
  subtitle: { color: colors.textSecondary, marginTop: 6, marginBottom: spacing.xl },
  metadata: { gap: spacing.xs },
  metaLabel: { color: colors.muted, fontSize: 9, fontWeight: '900', marginTop: spacing.sm },
  metaValue: { color: colors.textSecondary, fontSize: 11 },
  center: { flex: 1, justifyContent: 'center', padding: spacing.xl },
  errorCard: { gap: spacing.md, borderColor: colors.dangerBorder },
  errorTitle: { color: colors.danger, fontWeight: '900', fontSize: 16 },
  errorText: { color: colors.textSecondary, lineHeight: 19 },
  refreshError: { color: colors.warning, marginTop: spacing.md, fontSize: 11 }
});
