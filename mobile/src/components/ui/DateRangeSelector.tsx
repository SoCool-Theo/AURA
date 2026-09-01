import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, spacing } from '../../theme/theme';

export type DateRange = '1M' | '3M' | '6M' | '1Y' | 'ALL';
const ranges: DateRange[] = ['1M', '3M', '6M', '1Y', 'ALL'];

export function DateRangeSelector({ value, onChange }: { value: DateRange; onChange: (value: DateRange) => void }) {
  return (
    <View style={styles.row}>
      {ranges.map((range) => {
        const active = range === value;
        return (
          <Pressable key={range} onPress={() => onChange(range)} style={[styles.item, active && styles.active]}>
            <Text style={[styles.text, active && styles.activeText]}>{range}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    gap: spacing.xs,
    backgroundColor: colors.surfaceAlt,
    borderRadius: 12,
    padding: 4
  },
  item: {
    flex: 1,
    minHeight: 32,
    borderRadius: 9,
    alignItems: 'center',
    justifyContent: 'center'
  },
  active: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  text: { color: colors.muted, fontSize: 10, fontWeight: '800' },
  activeText: { color: colors.primary }
});
