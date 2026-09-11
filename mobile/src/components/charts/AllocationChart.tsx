import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { colors, spacing } from '../../theme/theme';

export function AllocationChart({ data }: { data: Array<{ symbol: string; weight: number }> }) {
  return (
    <View style={styles.wrapper}>
      {data.map((item) => (
        <View key={item.symbol} style={styles.row}>
          <View style={styles.labelRow}>
            <Text style={styles.symbol}>{item.symbol}</Text>
            <Text style={styles.weight}>{item.weight}%</Text>
          </View>
          <View style={styles.track}>
            <View style={[styles.fill, { width: `${Math.max(3, item.weight)}%` }]} />
          </View>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: { gap: spacing.md },
  row: { gap: 6 },
  labelRow: { flexDirection: 'row', justifyContent: 'space-between' },
  symbol: { color: colors.text, fontWeight: '800' },
  weight: { color: colors.textSecondary },
  track: { height: 8, borderRadius: 999, backgroundColor: colors.border, overflow: 'hidden' },
  fill: { height: '100%', backgroundColor: colors.primary, borderRadius: 999 }
});
