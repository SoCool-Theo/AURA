import React, { useMemo, useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { EmptyState } from '../../components/ui/EmptyState';
import { useAppData } from '../../hooks/useAppData';
import { scenarioCatalog } from '../../mocks/scenarios.mock';
import { colors, spacing, typography } from '../../theme/theme';

export function CombinedSimulationScreen({ route, navigation }: { route: any; navigation: any }) {
  const { portfolios, activePortfolio, runCombined } = useAppData();
  const portfolioId = route.params?.portfolioId ?? activePortfolio?.id;
  const portfolio = portfolios.find((item) => item.id === portfolioId) ?? activePortfolio;
  const [scenarioId, setScenarioId] = useState(scenarioCatalog[0].id);

  const initial = useMemo(
    () => Object.fromEntries((portfolio?.holdings ?? []).map((holding) => [holding.symbol, String(holding.weight)])),
    [portfolio?.id]
  );
  const [weights, setWeights] = useState<Record<string, string>>(initial);

  if (!portfolio || !portfolio.holdings.length) {
    return <SafeAreaView style={styles.safe}><EmptyState title="No holdings available" description="Add assets before running Combined Simulation." /></SafeAreaView>;
  }

  const selectedPortfolio = portfolio;
  const total = selectedPortfolio.holdings.reduce((sum, holding) => sum + Number(weights[holding.symbol] || 0), 0);

  async function run() {
    if (Math.abs(total - 100) > 0.05) {
      Alert.alert('Weights must total 100%', `Current total is ${total.toFixed(2)}%.`);
      return;
    }
    const numeric = Object.fromEntries(Object.entries(weights).map(([symbol, value]) => [symbol, Number(value)]));
    const record = await runCombined(selectedPortfolio.id, scenarioId, numeric);
    if (record) navigation.replace('SimulationResult', { simulationId: record.id });
  }

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Text style={styles.title}>Combined Simulation</Text>
        <Text style={styles.subtitle}>Choose a historical event, change the allocation, then compare both versions.</Text>

        <Text style={styles.sectionLabel}>Scenario</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.scenarioRow}>
          {scenarioCatalog.map((scenario) => (
            <Pressable
              key={scenario.id}
              onPress={() => setScenarioId(scenario.id)}
              style={[styles.scenarioChip, scenarioId === scenario.id && styles.scenarioChipActive]}
            >
              <Text style={[styles.scenarioText, scenarioId === scenario.id && styles.scenarioTextActive]}>
                {scenario.name}
              </Text>
            </Pressable>
          ))}
        </ScrollView>

        <View style={styles.totalRow}>
          <Text style={styles.sectionLabel}>Modified allocation</Text>
          <Text style={[styles.totalText, Math.abs(total - 100) > 0.05 && { color: colors.warning }]}>
            {total.toFixed(2)}%
          </Text>
        </View>

        <View style={styles.list}>
          {selectedPortfolio.holdings.map((holding) => (
            <Card key={holding.symbol} style={styles.row}>
              <View style={{ flex: 1 }}>
                <Text style={styles.symbol}>{holding.symbol}</Text>
                <Text style={styles.name}>{holding.name}</Text>
              </View>
              <View style={styles.weightInputBox}>
                <TextInput
                  value={weights[holding.symbol]}
                  onChangeText={(text) => setWeights((current) => ({ ...current, [holding.symbol]: text }))}
                  keyboardType="decimal-pad"
                  style={styles.input}
                  placeholderTextColor={colors.muted}
                />
                <Text style={styles.percent}>%</Text>
              </View>
            </Card>
          ))}
        </View>

        <Button title="Run combined simulation" onPress={run} style={{ marginTop: spacing.xl }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 100 },
  title: { color: colors.text, ...typography.h1 },
  subtitle: { color: colors.textSecondary, marginTop: 6, marginBottom: spacing.xl, lineHeight: 20 },
  sectionLabel: { color: colors.muted, fontSize: 11, fontWeight: '900', letterSpacing: 1, marginBottom: spacing.sm },
  scenarioRow: { gap: spacing.sm, paddingBottom: spacing.xl },
  scenarioChip: { maxWidth: 210, paddingHorizontal: 14, paddingVertical: 11, borderRadius: 14, backgroundColor: colors.surfaceAlt, borderWidth: 1, borderColor: colors.border },
  scenarioChipActive: { borderColor: colors.primary, backgroundColor: colors.selectedBackground },
  scenarioText: { color: colors.textSecondary, fontSize: 12, fontWeight: '800' },
  scenarioTextActive: { color: colors.primary },
  totalRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  totalText: { color: colors.primary, fontWeight: '900' },
  list: { gap: spacing.md },
  row: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  symbol: { color: colors.text, fontWeight: '900', fontSize: 16 },
  name: { color: colors.textSecondary, marginTop: 3, fontSize: 12 },
  weightInputBox: { flexDirection: 'row', alignItems: 'center', width: 105, backgroundColor: colors.surfaceAlt, borderWidth: 1, borderColor: colors.border, borderRadius: 14, paddingRight: 12 },
  input: { flex: 1, minHeight: 46, color: colors.text, textAlign: 'right', paddingHorizontal: 10, fontWeight: '900' },
  percent: { color: colors.muted, fontWeight: '800' }
});
