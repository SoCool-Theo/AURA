import React, { useMemo, useState } from 'react';
import { Alert, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { EmptyState } from '../../components/ui/EmptyState';
import { useAppData } from '../../hooks/useAppData';
import { colors, spacing, typography } from '../../theme/theme';

export function AllocationChangeScreen({ route, navigation }: { route: any; navigation: any }) {
  const { portfolios, activePortfolio, runAllocation } = useAppData();
  const portfolioId = route.params?.portfolioId ?? activePortfolio?.id;
  const portfolio = portfolios.find((item) => item.id === portfolioId) ?? activePortfolio;

  const initial = useMemo(
    () => Object.fromEntries((portfolio?.holdings ?? []).map((holding) => [holding.symbol, String(holding.weight)])),
    [portfolio?.id]
  );
  const [weights, setWeights] = useState<Record<string, string>>(initial);

  if (!portfolio || !portfolio.holdings.length) {
    return <SafeAreaView style={styles.safe}><EmptyState title="No holdings available" description="Add assets before changing allocation." /></SafeAreaView>;
  }

  const selectedPortfolio = portfolio;
  const total = selectedPortfolio.holdings.reduce((sum, holding) => sum + Number(weights[holding.symbol] || 0), 0);

  async function run() {
    if (Math.abs(total - 100) > 0.05) {
      Alert.alert('Weights must total 100%', `Current total is ${total.toFixed(2)}%.`);
      return;
    }
    const numeric = Object.fromEntries(Object.entries(weights).map(([symbol, value]) => [symbol, Number(value)]));
    const record = await runAllocation(selectedPortfolio.id, numeric);
    if (record) navigation.replace('SimulationResult', { simulationId: record.id });
  }

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Text style={styles.title}>Allocation Change</Text>
        <Text style={styles.subtitle}>Edit percentages for the same assets and compare the frontend demo metrics.</Text>

        <Card style={styles.totalCard}>
          <Text style={styles.totalLabel}>TOTAL ALLOCATION</Text>
          <Text style={[styles.totalValue, Math.abs(total - 100) > 0.05 && { color: colors.warning }]}>
            {total.toFixed(2)}%
          </Text>
        </Card>

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

        <Button title="Compare allocation" onPress={run} style={{ marginTop: spacing.xl }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 100 },
  title: { color: colors.text, ...typography.h1 },
  subtitle: { color: colors.textSecondary, marginTop: 6, marginBottom: spacing.xl, lineHeight: 20 },
  totalCard: { alignItems: 'center', gap: 4, marginBottom: spacing.lg },
  totalLabel: { color: colors.muted, fontSize: 10, fontWeight: '900', letterSpacing: 1.2 },
  totalValue: { color: colors.primary, fontSize: 28, fontWeight: '900' },
  list: { gap: spacing.md },
  row: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  symbol: { color: colors.text, fontWeight: '900', fontSize: 16 },
  name: { color: colors.textSecondary, marginTop: 3, fontSize: 12 },
  weightInputBox: { flexDirection: 'row', alignItems: 'center', width: 105, backgroundColor: colors.surfaceAlt, borderWidth: 1, borderColor: colors.border, borderRadius: 14, paddingRight: 12 },
  input: { flex: 1, minHeight: 46, color: colors.text, textAlign: 'right', paddingHorizontal: 10, fontWeight: '900' },
  percent: { color: colors.muted, fontWeight: '800' }
});
