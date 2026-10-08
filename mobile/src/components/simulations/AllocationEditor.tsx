import React, { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import type { PortfolioResponse } from '../../types/portfolio';
import {
  isAllocationPercentInput,
  type AllocationInputs
} from '../../simulation/simulationValidation';
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
  onChange: (symbol: string, value: string, selectedSymbols: readonly string[]) => void;
}) {
  const symbols = portfolio.holdings.map((holding) => holding.symbol);
  const symbolKey = symbols.join('|');
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>(() => symbols.slice(0, 2));
  useEffect(() => setSelectedSymbols(symbols.slice(0, 2)), [portfolio.id, symbolKey]);
  const totalIsValid = Math.abs(total - 100) <= 1e-7;
  function toggleTarget(symbol: string) {
    setSelectedSymbols((current) => current.includes(symbol)
      ? current.filter((currentSymbol) => currentSymbol !== symbol)
      : current.length < 2 ? [...current, symbol] : current);
  }
  return (
    <>
      <Card style={styles.totalCard}>
        <Text style={styles.totalLabel}>TOTAL ALLOCATION</Text>
        <Text style={[styles.totalValue, !totalIsValid && styles.invalid]}>
          {total.toFixed(2)}%
        </Text>
        <Text style={styles.targetHelp}>Select exactly two assets to exchange allocation.</Text>
        <Text style={styles.targetStatus}>
          {selectedSymbols.length === 2
            ? `${selectedSymbols[0]} ↔ ${selectedSymbols[1]}`
            : `${selectedSymbols.length}/2 selected · Choose one more asset`}
        </Text>
      </Card>
      <View style={styles.list}>
        {portfolio.holdings.map((holding) => {
          const selected = selectedSymbols.includes(holding.symbol);
          const selectionDisabled = disabled || (!selected && selectedSymbols.length >= 2);
          return (
          <Pressable
            key={holding.symbol}
            accessibilityRole="checkbox"
            accessibilityLabel={`${holding.symbol} allocation target`}
            accessibilityState={{ checked: selected, disabled: selectionDisabled }}
            disabled={selectionDisabled}
            onPress={() => toggleTarget(holding.symbol)}
            style={selectionDisabled && !selected ? styles.disabledCard : undefined}
          >
          <Card style={[styles.row, selected && styles.selectedRow]}>
            <View style={{ flex: 1 }}>
              <Text style={styles.symbol}>{holding.symbol}</Text>
              <Text style={styles.position}>Saved position {holding.position + 1}</Text>
              <View style={styles.targetButton}>
                <Text style={[styles.targetButtonText, selected && styles.selectedTargetText]}>
                  {selected ? '✓ Target selected' : 'Select target'}
                </Text>
              </View>
            </View>
            <View style={[styles.inputBox, !selected && styles.disabledInputBox]}>
              <TextInput
                accessibilityLabel={`${holding.symbol} modified allocation percent`}
                accessibilityState={{ disabled: disabled || !selected || selectedSymbols.length !== 2 }}
                editable={!disabled && selected && selectedSymbols.length === 2}
                onPressIn={(event) => event.stopPropagation()}
                value={inputs[holding.symbol] ?? ''}
                onChangeText={(value) => {
                  if (isAllocationPercentInput(value)) {
                    onChange(holding.symbol, value, selectedSymbols);
                  }
                }}
                onBlur={() => {
                  const value = inputs[holding.symbol]?.trim() ?? '';
                  const percent = Number(value);
                  if (value && Number.isFinite(percent) && percent >= 0 && percent <= 100) {
                    onChange(holding.symbol, percent.toFixed(2), selectedSymbols);
                  }
                }}
                keyboardType="decimal-pad"
                style={styles.input}
                placeholder="0"
                placeholderTextColor={colors.muted}
              />
              <Text style={styles.percent}>%</Text>
            </View>
          </Card>
          </Pressable>
          );
        })}
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  totalCard: { alignItems: 'center', gap: spacing.xs, marginBottom: spacing.lg },
  totalLabel: { color: colors.muted, fontSize: 10, fontWeight: '900', letterSpacing: 1.2 },
  totalValue: { color: colors.primary, fontSize: 27, fontWeight: '900' },
  targetHelp: { color: colors.textSecondary, fontSize: 11, textAlign: 'center' },
  targetStatus: { color: colors.primary, fontSize: 12, fontWeight: '900', textAlign: 'center' },
  invalid: { color: colors.warning },
  list: { gap: spacing.md },
  row: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  disabledCard: { opacity: 0.68 },
  selectedRow: { borderColor: colors.primary },
  symbol: { color: colors.text, fontWeight: '900', fontSize: 16 },
  position: { color: colors.textSecondary, fontSize: 11, marginTop: spacing.xs },
  targetButton: { alignSelf: 'flex-start', marginTop: spacing.sm, paddingVertical: 5, paddingHorizontal: 8, borderRadius: 8, backgroundColor: colors.surfaceAlt },
  targetButtonText: { color: colors.textSecondary, fontSize: 10, fontWeight: '800' },
  selectedTargetText: { color: colors.primary },
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
  disabledInputBox: { opacity: 0.45 },
  input: { flex: 1, minHeight: 46, color: colors.text, textAlign: 'right', paddingHorizontal: 10, fontWeight: '900' },
  percent: { color: colors.muted, fontWeight: '800' }
});
