import React, { useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { useAppData } from '../../hooks/useAppData';
import { scenarioCatalog } from '../../mocks/scenarios.mock';
import { colors, spacing, typography } from '../../theme/theme';

export function HistoricalScenarioScreen({ route, navigation }: { route: any; navigation: any }) {
  const { activePortfolio, runHistorical } = useAppData();
  const portfolioId = route.params?.portfolioId ?? activePortfolio?.id;
  const [selectedId, setSelectedId] = useState(scenarioCatalog[0].id);

  async function run() {
    if (!portfolioId) {
      Alert.alert('No portfolio', 'Select a portfolio first.');
      return;
    }
    const record = await runHistorical(portfolioId, selectedId);
    if (record) navigation.replace('SimulationResult', { simulationId: record.id });
  }

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Historical Scenario</Text>
        <Text style={styles.subtitle}>Choose one of Aura’s five educational event definitions.</Text>

        <View style={styles.list}>
          {scenarioCatalog.map((scenario) => (
            <Pressable key={scenario.id} onPress={() => setSelectedId(scenario.id)}>
              <Card style={[styles.card, selectedId === scenario.id && styles.selected]}>
                <View style={styles.cardTop}>
                  <Text style={styles.name}>{scenario.name}</Text>
                  <View style={[styles.radio, selectedId === scenario.id && styles.radioSelected]} />
                </View>
                <Text style={styles.period}>{scenario.period}</Text>
                <Text style={styles.description}>{scenario.description}</Text>
              </Card>
            </Pressable>
          ))}
        </View>

        <Button title="Run historical scenario" onPress={run} style={{ marginTop: spacing.xl }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 100 },
  title: { color: colors.text, ...typography.h1 },
  subtitle: { color: colors.textSecondary, marginTop: 6, marginBottom: spacing.xl, lineHeight: 20 },
  list: { gap: spacing.md },
  card: { gap: spacing.sm },
  selected: { borderColor: colors.primary, backgroundColor: colors.summaryBackground },
  cardTop: { flexDirection: 'row', justifyContent: 'space-between', gap: spacing.md, alignItems: 'center' },
  name: { color: colors.text, fontSize: 16, fontWeight: '900', flex: 1 },
  period: { color: colors.primary, fontSize: 12, fontWeight: '800' },
  description: { color: colors.textSecondary, lineHeight: 19, fontSize: 13 },
  radio: { width: 18, height: 18, borderRadius: 99, borderWidth: 2, borderColor: colors.border },
  radioSelected: { borderColor: colors.primary, backgroundColor: colors.primary }
});
