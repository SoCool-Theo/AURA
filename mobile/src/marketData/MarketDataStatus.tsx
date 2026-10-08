import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { colors } from '../theme/theme';
import { marketDataPresentation } from './marketDataPresentation';
import { useMarketDataRefresh } from './useMarketDataRefresh';

type Props = { market: ReturnType<typeof useMarketDataRefresh>; symbols: string[] };
export function MarketDataStatus({ market, symbols }: Props) {
  const info = marketDataPresentation(market.status, market.unavailable, symbols);
  return <View style={styles.row} accessibilityLiveRegion="polite">
    <View style={styles.heading}><View style={[styles.dot, { backgroundColor: colors[info.tone === 'muted' ? 'muted' : info.tone] }]} /><Text style={[styles.title, { color: colors[info.tone === 'muted' ? 'textSecondary' : info.tone] }]}>{info.title}</Text></View>
    <Text style={styles.detail}>{info.detail}</Text>
  </View>;
}
const styles = StyleSheet.create({
  row: { marginTop: 12, padding: 10, borderWidth: 1, borderColor: colors.border, borderRadius: 12, backgroundColor: colors.surface },
  heading: { flexDirection: 'row', alignItems: 'center', gap: 7 },
  dot: { width: 6, height: 6, borderRadius: 3 },
  title: { flex: 1, fontSize: 11, fontWeight: '800' },
  detail: { marginTop: 4, fontSize: 10, lineHeight: 16, color: colors.muted },
});
