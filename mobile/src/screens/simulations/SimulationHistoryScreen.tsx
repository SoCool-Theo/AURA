import React from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { useAppData } from '../../hooks/useAppData';
import { colors, spacing, typography } from '../../theme/theme';
import { formatPercent } from '../../utils/formatting';

export function SimulationHistoryScreen({ navigation }: { navigation: any }) {
  const { simulations, deleteSimulation } = useAppData();

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Simulation History</Text>
        <Text style={styles.subtitle}>Every local run is saved here until you remove it.</Text>

        {simulations.length ? (
          <View style={styles.list}>
            {simulations.map((record) => (
              <Pressable
                key={record.id}
                onPress={() => navigation.navigate('SimulationResult', { simulationId: record.id })}
              >
                <Card style={styles.card}>
                  <View style={styles.top}>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.mode}>{record.mode}</Text>
                      <Text style={styles.name}>{record.title}</Text>
                      <Text style={styles.meta}>{record.portfolioName} · {new Date(record.createdAt).toLocaleDateString()}</Text>
                    </View>
                    <Pressable
                      onPress={() => Alert.alert('Delete simulation?', 'Remove this local history record?', [
                        { text: 'Cancel', style: 'cancel' },
                        { text: 'Delete', style: 'destructive', onPress: () => deleteSimulation(record.id) }
                      ])}
                      style={styles.delete}
                    >
                      <Ionicons name="trash-outline" size={18} color={colors.danger} />
                    </Pressable>
                  </View>
                  <View style={styles.metrics}>
                    <Text style={styles.metric}>Return {formatPercent(record.original.cumulativeReturn)}</Text>
                    <Text style={styles.metric}>Drawdown {formatPercent(record.original.maxDrawdown)}</Text>
                  </View>
                </Card>
              </Pressable>
            ))}
          </View>
        ) : (
          <Card>
            <EmptyState
              icon="pulse-outline"
              title="No simulations yet"
              description="Run Historical, Allocation or Combined Simulation and the result will appear here."
            />
          </Card>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 100 },
  title: { color: colors.text, ...typography.h1 },
  subtitle: { color: colors.textSecondary, marginTop: 6, marginBottom: spacing.xl },
  list: { gap: spacing.md },
  card: { gap: spacing.md },
  top: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.md },
  mode: { color: colors.primary, fontSize: 10, fontWeight: '900', letterSpacing: 1 },
  name: { color: colors.text, fontSize: 16, fontWeight: '900', marginTop: 4 },
  meta: { color: colors.muted, fontSize: 12, marginTop: 4 },
  delete: { width: 40, height: 40, borderRadius: 13, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surfaceAlt },
  metrics: { flexDirection: 'row', gap: spacing.lg },
  metric: { color: colors.textSecondary, fontWeight: '700', fontSize: 12 }
});
