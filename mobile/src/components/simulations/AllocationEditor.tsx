import React from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';

import type { PortfolioResponse } from '../../types/portfolio';
import type { AllocationInputs } from '../../simulation/simulationValidation';
import { Card } from '../ui/Card';
import { colors, spacing } from '../../theme/theme';

export function AllocationEditor({
  portfolio,
  inputs,
  total,
  disabled = false,
  onChange
}: {
  portfolio: PortfolioResponse;
  inputs: AllocationInputs;
  total: number;
  disabled?: boolean;
  onChange: (symbol: string, value: string) => void;
}) {
  const totalIsValid = Math.abs(total - 100) <= 1e-7;
  return (
    <>
      <Card style={styles.totalCard}>
        <Text style={styles.totalLabel}>TOTAL ALLOCATION</Text>
        <Text style={[styles.totalValue, !totalIsValid && styles.invalid]}>
          {total.toFixed(2)}%
        </Text>
      </Card>
      <View style={styles.list}>
        {portfolio.holdings.map((holding) => (
          <Card key={holding.symbol} style={styles.row}>
            <View style={{ flex: 1 }}>
              <Text style={styles.symbol}>{holding.symbol}</Text>
              <Text style={styles.position}>Saved position {holding.position + 1}</Text>
            </View>
            <View style={styles.inputBox}>
              <TextInput
                accessibilityLabel={`${holding.symbol} modified allocation percent`}
                accessibilityState={{ disabled }}
                editable={!disabled}
                value={inputs[holding.symbol] ?? ''}
                onChangeText={(value) => onChange(holding.symbol, value)}
                keyboardType="decimal-pad"
                style={styles.input}
                placeholder="0"
                placeholderTextColor={colors.muted}
              />
              <Text style={styles.percent}>%</Text>
            </View>
          </Card>
        ))}
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  totalCard: { alignItems: 'center', gap: spacing.xs, marginBottom: spacing.lg },
  totalLabel: { color: colors.muted, fontSize: 10, fontWeight: '900', letterSpacing: 1.2 },
  totalValue: { color: colors.primary, fontSize: 27, fontWeight: '900' },
  invalid: { color: colors.warning },
  list: { gap: spacing.md },
  row: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  symbol: { color: colors.text, fontWeight: '900', fontSize: 16 },
  position: { color: colors.textSecondary, fontSize: 11, marginTop: spacing.xs },
  inputBox: {
    width: 108,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surfaceAlt,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 14,
    paddingRight: spacing.md
  },
  input: { flex: 1, minHeight: 46, color: colors.text, textAlign: 'right', paddingHorizontal: 10, fontWeight: '900' },
  percent: { color: colors.muted, fontWeight: '800' }
});
