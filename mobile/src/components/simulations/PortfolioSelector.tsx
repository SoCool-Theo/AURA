import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text } from 'react-native';

import type { PortfolioSummaryResponse } from '../../types/portfolio';
import { colors, spacing } from '../../theme/theme';

export function PortfolioSelector({
  portfolios,
  selectedId,
  disabled = false,
  onSelect
}: {
  portfolios: PortfolioSummaryResponse[];
  selectedId: string | null;
  disabled?: boolean;
  onSelect: (portfolioId: string) => void;
}) {
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.row}
    >
      {portfolios.map((portfolio) => {
        const selected = portfolio.id === selectedId;
        return (
          <Pressable
            disabled={disabled}
            key={portfolio.id}
            onPress={() => onSelect(portfolio.id)}
            style={[styles.chip, selected && styles.selected]}
          >
            <Text style={[styles.text, selected && styles.selectedText]}>
              {portfolio.name}
            </Text>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  row: { gap: spacing.sm, paddingBottom: spacing.lg },
  chip: {
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 14,
    backgroundColor: colors.surfaceAlt,
    borderWidth: 1,
    borderColor: colors.border
  },
  selected: { borderColor: colors.primary, backgroundColor: colors.selectedBackground },
  text: { color: colors.textSecondary, fontSize: 12, fontWeight: '800' },
  selectedText: { color: colors.primary }
});
