import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Card } from './Card';
import { colors, spacing } from '../../theme/theme';

export function WebKpiCard({
  icon,
  label,
  value,
  meta,
  tone = 'primary',
  onPress,
  accessibilityHint
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  value: string;
  meta?: string;
  tone?: 'primary' | 'success' | 'warning' | 'danger' | 'blue';
  onPress?: () => void;
  accessibilityHint?: string;
}) {
  const toneMap = {
    primary: { fg: colors.primary, bg: colors.cyanBackground },
    success: { fg: colors.success, bg: colors.positiveBackground },
    warning: { fg: colors.warning, bg: colors.warningBackground },
    danger: { fg: colors.danger, bg: colors.negativeBackground },
    blue: { fg: colors.blue, bg: colors.blueBackground }
  } as const;
  const selected = toneMap[tone];

  const contents = (
    <>
      <View style={styles.topRow}>
        <View style={[styles.iconBox, { backgroundColor: selected.bg }]}>
          <Ionicons name={icon} size={19} color={selected.fg} />
        </View>
        {onPress ? <Ionicons name="chevron-forward" size={17} color={colors.muted} /> : null}
      </View>
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.value}>{value}</Text>
      {meta ? <Text style={[styles.meta, { color: selected.fg }]}>{meta}</Text> : null}
    </>
  );

  if (!onPress) return <Card style={styles.card}>{contents}</Card>;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${label}: ${value}`}
      accessibilityHint={accessibilityHint}
      onPress={onPress}
      style={({ pressed }) => [styles.pressable, pressed && styles.pressed]}
    >
      <Card style={styles.interactiveCard}>{contents}</Card>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    flexGrow: 1,
    flexBasis: 140,
    minHeight: 128,
    gap: spacing.sm
  },
  pressable: {
    flexGrow: 1,
    flexBasis: 140
  },
  pressed: { opacity: 0.76 },
  interactiveCard: {
    minHeight: 128,
    gap: spacing.sm
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between'
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
