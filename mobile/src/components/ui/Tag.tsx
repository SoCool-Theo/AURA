import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { colors } from '../../theme/colors';

export function Tag({
  label,
  tone = 'default'
}: {
  label: string;
  tone?: 'default' | 'success' | 'warning' | 'danger' | 'primary';
}) {
  const map = {
    default: { bg: colors.surfaceAlt, fg: colors.textSecondary },
    success: { bg: colors.positiveBackground, fg: colors.success },
    warning: { bg: colors.warningBackground, fg: colors.warning },
    danger: { bg: colors.negativeBackground, fg: colors.danger },
    primary: { bg: colors.cyanBackground, fg: colors.primary }
  };
  const selected = map[tone];
  return (
    <View style={[styles.tag, { backgroundColor: selected.bg }]}>
      <Text style={[styles.text, { color: selected.fg }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  tag: { alignSelf: 'flex-start', borderRadius: 999, paddingHorizontal: 9, paddingVertical: 5 },
  text: { fontSize: 10, fontWeight: '900' }
});
