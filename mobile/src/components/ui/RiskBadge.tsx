import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { colors } from '../../theme/colors';

export function RiskBadge({ level }: { level: string }) {
  const lower = level.toLowerCase();
  const color = lower.includes('high')
    ? colors.danger
    : lower.includes('low')
      ? colors.success
      : colors.warning;

  return (
    <View style={[styles.badge, { borderColor: color }]}>
      <Text style={[styles.text, { color }]}>{level}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 5
  },
  text: { fontWeight: '800', fontSize: 12 }
});
