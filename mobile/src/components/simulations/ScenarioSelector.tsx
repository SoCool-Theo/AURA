import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { HistoricalScenarioResponse } from '../../types/simulation';
import { Card } from '../ui/Card';
import { colors, spacing } from '../../theme/theme';

export function ScenarioSelector({
  scenarios,
  selectedId,
  disabled = false,
  onSelect
}: {
  scenarios: HistoricalScenarioResponse[];
  selectedId: string | null;
  disabled?: boolean;
  onSelect: (scenarioId: string) => void;
}) {
  return (
    <View style={styles.list}>
      {scenarios.map((scenario) => {
        const selected = scenario.id === selectedId;
        return (
          <Pressable
            accessibilityLabel={`${scenario.display_name} scenario`}
            accessibilityRole="radio"
            accessibilityState={{ selected, disabled }}
            disabled={disabled}
            key={scenario.id}
            onPress={() => onSelect(scenario.id)}
          >
            <Card style={[styles.card, selected && styles.selected]}>
              <View style={styles.top}>
                <Text style={styles.name}>{scenario.display_name}</Text>
                <View style={[styles.radio, selected && styles.radioSelected]} />
              </View>
              <Text style={styles.period}>
                {scenario.requested_start_date} → {scenario.requested_end_date}
              </Text>
              <Text style={styles.id}>ID · {scenario.id}</Text>
              <Text style={styles.description}>{scenario.description}</Text>
            </Card>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  list: { gap: spacing.md },
  card: { gap: spacing.sm },
  selected: { borderColor: colors.primary, backgroundColor: colors.summaryBackground },
  top: { flexDirection: 'row', justifyContent: 'space-between', gap: spacing.md },
  name: { flex: 1, color: colors.text, fontSize: 15, fontWeight: '900' },
  period: { color: colors.primary, fontSize: 11, fontWeight: '800' },
  id: { color: colors.muted, fontSize: 9 },
  description: { color: colors.textSecondary, fontSize: 12, lineHeight: 18 },
  radio: { width: 18, height: 18, borderRadius: 9, borderWidth: 2, borderColor: colors.border },
  radioSelected: { borderColor: colors.primary, backgroundColor: colors.primary }
});
