import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { DemoHolding as Holding } from '../../types/demo';
import { RiskBadge } from '../ui/RiskBadge';
import { colors, spacing } from '../../theme/theme';
import { formatCurrency } from '../../utils/formatting';

export function AssetRow({ holding }: { holding: Holding }) {
  return (
    <View style={styles.row}>
      <View style={styles.symbolBox}>
        <Text style={styles.symbol}>{holding.symbol.slice(0, 4)}</Text>
      </View>
      <View style={styles.middle}>
        <Text style={styles.name}>{holding.name}</Text>
        <Text style={styles.meta}>{holding.weight}% weight · {formatCurrency(holding.value)}</Text>
      </View>
      <RiskBadge level={holding.risk} />
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, paddingVertical: 12 },
  symbolBox: {
    width: 44, height: 44, borderRadius: 14, backgroundColor: colors.surfaceAlt,
    alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: colors.border
  },
  symbol: { color: colors.primary, fontWeight: '900', fontSize: 11 },
  middle: { flex: 1 },
  name: { color: colors.text, fontWeight: '800' },
  meta: { color: colors.muted, marginTop: 4, fontSize: 12 }
});
