import React from 'react';
import { StyleSheet, Text } from 'react-native';
import { Card } from '../ui/Card';
import { colors, spacing } from '../../theme/theme';

export function MetricCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Card style={styles.card}>
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.value}>{value}</Text>
      {hint ? <Text style={styles.hint}>{hint}</Text> : null}
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { width: '48%', gap: spacing.xs },
  label: { color: colors.muted, fontSize: 12, fontWeight: '700' },
  value: { color: colors.text, fontSize: 22, fontWeight: '800' },
  hint: { color: colors.textSecondary, fontSize: 11 }
});
