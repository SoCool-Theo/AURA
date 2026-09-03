import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { DimensionValue } from 'react-native';

import type { CorrelationPair } from '../../types/analytics';
import { colors, spacing } from '../../theme/theme';

function relationshipLabel(value: number | null): string {
  if (value === null) return 'Unavailable';
  const absolute = Math.abs(value);
  if (value <= -0.5) return 'Strong negative';
  if (value < 0) return 'Negative';
  if (absolute >= 0.75) return 'Strong positive';
  if (absolute >= 0.5) return 'Moderate positive';
  if (absolute >= 0.25) return 'Weak positive';
  return 'Low relationship';
}

export function AssetRelationshipBars({
  pairs
}: {
  pairs: CorrelationPair[];
}) {
  if (!pairs.length) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyTitle}>No asset pairs</Text>
        <Text style={styles.emptyText}>
          A single-asset report does not have pairwise correlations.
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {pairs.map((pair) => {
        const positive = pair.correlation !== null && pair.correlation >= 0;
        const width: DimensionValue = pair.correlation === null
          ? '0%'
          : `${Math.max(2, Math.abs(pair.correlation) * 100)}%`;

        return (
          <View key={`${pair.asset_a}-${pair.asset_b}`} style={styles.row}>
            <View style={styles.topRow}>
              <Text style={styles.pair}>
                {pair.asset_a} <Text style={styles.arrow}>↔</Text> {pair.asset_b}
              </Text>
              <Text
                style={[
                  styles.value,
                  { color: pair.correlation === null
                    ? colors.muted
                    : positive ? colors.primary : colors.danger }
                ]}
              >
                {pair.correlation === null ? 'N/A' : pair.correlation.toFixed(3)}
              </Text>
            </View>
            <View style={styles.track}>
              <View
                style={[
                  styles.fill,
                  {
                    width,
                    backgroundColor: positive ? colors.primary : colors.danger
                  }
                ]}
              />
            </View>
            <Text style={styles.label}>{relationshipLabel(pair.correlation)}</Text>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: spacing.lg },
  row: { gap: 7 },
  topRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  pair: { color: colors.text, fontSize: 13, fontWeight: '900' },
  arrow: { color: colors.muted },
  value: { fontSize: 13, fontWeight: '900' },
  track: {
    height: 8,
    borderRadius: 999,
    backgroundColor: colors.border,
    overflow: 'hidden'
  },
  fill: { height: '100%', borderRadius: 999 },
  label: { color: colors.muted, fontSize: 10, fontWeight: '700' },
  empty: { alignItems: 'center', paddingVertical: spacing.xl, gap: spacing.sm },
  emptyTitle: { color: colors.text, fontWeight: '900' },
  emptyText: {
    color: colors.muted,
    fontSize: 11,
    textAlign: 'center'
  }
});
