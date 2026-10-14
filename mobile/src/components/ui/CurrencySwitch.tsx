import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import type { CurrencyDisplayContext, DisplayCurrency } from '../../currencyDisplay';
import { colors } from '../../theme/theme';

export function CurrencySwitch({ display, value, onChange, saved = false }: {
  display: CurrencyDisplayContext; value: DisplayCurrency; onChange: (value: DisplayCurrency) => void; saved?: boolean;
}) {
  return <View style={styles.control}>
    <View style={styles.options} accessibilityRole="radiogroup">
      {(['USD', 'THB'] as const).map(currency => {
        const disabled = !display.views.some(view => view.currency === currency);
        return <Pressable key={currency} accessibilityRole="radio" accessibilityLabel={`Display currency ${currency}`}
          accessibilityState={{ selected: value === currency, disabled }} disabled={disabled}
          onPress={() => onChange(currency)} style={[styles.option, value === currency && styles.selected, disabled && styles.disabled]}>
          <Text style={[styles.text, value === currency && styles.selectedText]}>{currency}</Text>
        </Pressable>;
      })}
    </View>
    <Text style={styles.note}>{display.fx && display.views.length === 1 ? 'Currency conversion is unavailable for one or more displayed horizons.'
      : display.fx ? `${saved ? 'Saved ' : ''}USD/THB ${display.fx.rate} as of ${display.fx.as_of}. Display currency does not change allocation or risk.`
      : saved ? 'Currency conversion is unavailable because this simulation has no saved exchange rate.'
        : 'Currency conversion is unavailable because fresh USD/THB data is unavailable.'}</Text>
  </View>;
}
const styles = StyleSheet.create({
  control: { gap: 8, marginVertical: 12 }, options: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  option: { minHeight: 44, borderWidth: 1, borderColor: colors.border, borderRadius: 10, paddingVertical: 10, paddingHorizontal: 16 },
  selected: { borderColor: colors.primary }, disabled: { opacity: .45 },
  text: { color: colors.textSecondary, fontSize: 13, fontWeight: '700' }, selectedText: { color: colors.primary },
  note: { color: colors.muted, fontSize: 12, lineHeight: 18 },
});
