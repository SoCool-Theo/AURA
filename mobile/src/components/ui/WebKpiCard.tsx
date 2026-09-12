import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Card } from './Card';
import { colors, spacing } from '../../theme/theme';

export function WebKpiCard({
  icon,
  label,
  value,
  meta,
  tone = 'primary'
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  value: string;
  meta?: string;
  tone?: 'primary' | 'success' | 'warning' | 'danger' | 'blue';
}) {
  const toneMap = {
    primary: { fg: colors.primary, bg: colors.cyanBackground },
    success: { fg: colors.success, bg: colors.positiveBackground },
    warning: { fg: colors.warning, bg: colors.warningBackground },
    danger: { fg: colors.danger, bg: colors.negativeBackground },
    blue: { fg: colors.blue, bg: colors.blueBackground }
  } as const;
  const selected = toneMap[tone];

  return (
    <Card style={styles.card}>
      <View style={[styles.iconBox, { backgroundColor: selected.bg }]}>
        <Ionicons name={icon} size={19} color={selected.fg} />
      </View>
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.value}>{value}</Text>
      {meta ? <Text style={[styles.meta, { color: selected.fg }]}>{meta}</Text> : null}
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    flexGrow: 1,
    flexBasis: 140,
    minHeight: 128,
    gap: spacing.sm
  },
  iconBox: {
    width: 36,
    height: 36,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center'
  },
  label: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: '700'
  },
  value: {
    color: colors.text,
    fontSize: 21,
    fontWeight: '900'
  },
  meta: {
    fontSize: 10,
    fontWeight: '800'
  }
});
