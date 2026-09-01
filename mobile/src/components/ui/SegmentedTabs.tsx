import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text } from 'react-native';
import { colors, spacing } from '../../theme/theme';

export function SegmentedTabs<T extends string>({
  items,
  value,
  onChange
}: {
  items: readonly T[];
  value: T;
  onChange: (item: T) => void;
}) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.row}>
      {items.map((item) => {
        const active = item === value;
        return (
          <Pressable
            key={item}
            onPress={() => onChange(item)}
            style={[styles.tab, active && styles.activeTab]}
          >
            <Text style={[styles.label, active && styles.activeLabel]}>{item}</Text>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  row: { gap: spacing.sm },
  tab: {
    minHeight: 38,
    paddingHorizontal: 14,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.surfaceAlt,
    borderWidth: 1,
    borderColor: colors.borderSoft
  },
  activeTab: {
    borderColor: colors.primary,
    backgroundColor: colors.selectedBackground
  },
  label: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: '800'
  },
  activeLabel: { color: colors.primary }
});
