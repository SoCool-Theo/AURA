import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { RiskDriver } from '../../types/analytics';
import { Card } from '../ui/Card';
import { RiskBadge } from '../ui/RiskBadge';
import { colors, spacing } from '../../theme/theme';

export function RiskDriverCard({ driver }: { driver: RiskDriver }) {
  return (
    <Card style={styles.card}>
      <View style={styles.top}>
        <Text style={styles.symbol}>{driver.symbol}</Text>
        <RiskBadge level={driver.level} />
      </View>
      <Text style={styles.text}>{driver.explanation}</Text>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { gap: spacing.sm },
  top: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  symbol: { color: colors.text, fontSize: 18, fontWeight: '900' },
  text: { color: colors.textSecondary, lineHeight: 20 }
});
