import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { DimensionValue } from 'react-native';
import type { DemoHolding as Holding } from '../../types/demo';
import { colors, spacing } from '../../theme/theme';

type Pair = {
  left: string;
  right: string;
  value: number;
};

const previewValues = [0.82, 0.66, 0.48, 0.27, -0.18, 0.12];

function labelFor(value: number) {
  const absolute = Math.abs(value);

  if (value < -0.15) return 'Negative';
  if (absolute >= 0.75) return 'Strong positive';
  if (absolute >= 0.5) return 'Moderate positive';
  if (absolute >= 0.25) return 'Weak positive';
  return 'Low relationship';
}

function buildPairs(holdings: Holding[]): Pair[] {
  const pairs: Pair[] = [];

  for (let i = 0; i < holdings.length; i += 1) {
    for (let j = i + 1; j < holdings.length; j += 1) {
      pairs.push({
        left: holdings[i].symbol,
        right: holdings[j].symbol,
        value: previewValues[pairs.length % previewValues.length]
      });

      if (pairs.length >= 5) return pairs;
    }
  }

  return pairs;
}

export function AssetRelationshipBars({ holdings }: { holdings: Holding[] }) {
  const pairs = buildPairs(holdings);

  if (pairs.length === 0) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyTitle}>Add at least two assets</Text>
        <Text style={styles.emptyText}>
          Asset relationships need multiple holdings to compare.
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {pairs.map((pair) => {
        const positive = pair.value >= 0;
        const width: DimensionValue = `${Math.max(8, Math.abs(pair.value) * 100)}%`;

        return (
          <View key={`${pair.left}-${pair.right}`} style={styles.row}>
            <View style={styles.topRow}>
              <Text style={styles.pair}>
                {pair.left} <Text style={styles.arrow}>↔</Text> {pair.right}
              </Text>
              <Text
                style={[
                  styles.value,
                  { color: positive ? colors.primary : colors.danger }
                ]}
              >
                {pair.value > 0 ? '+' : ''}
                {pair.value.toFixed(2)}
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

            <Text style={styles.label}>{labelFor(pair.value)}</Text>
          </View>
        );
      })}

      <Text style={styles.demoNote}>
        Demo relationship preview. Real correlation values will come from Aura's backend market data.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: spacing.lg
  },
  row: {
    gap: 7
  },
  topRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  pair: {
    color: colors.text,
    fontSize: 13,
    fontWeight: '900'
  },
  arrow: {
    color: colors.muted
  },
  value: {
    fontSize: 13,
    fontWeight: '900'
  },
  track: {
    height: 8,
    borderRadius: 999,
    backgroundColor: colors.border,
    overflow: 'hidden'
  },
  fill: {
    height: '100%',
    borderRadius: 999
  },
  label: {
    color: colors.muted,
    fontSize: 10,
    fontWeight: '700'
  },
  demoNote: {
    color: colors.muted,
    fontSize: 10,
    lineHeight: 15,
    paddingTop: spacing.xs
  },
  empty: {
    alignItems: 'center',
    paddingVertical: spacing.xl,
    gap: spacing.sm
  },
  emptyTitle: {
    color: colors.text,
    fontWeight: '900'
  },
  emptyText: {
    color: colors.muted,
    fontSize: 11,
    textAlign: 'center'
  }
});
