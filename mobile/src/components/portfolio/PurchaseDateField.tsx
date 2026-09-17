import DateTimePicker, {
  type DateTimePickerEvent
} from '@react-native-community/datetimepicker';
import { Ionicons } from '@expo/vector-icons';
import React, { useMemo, useState } from 'react';
import { Platform, Pressable, StyleSheet, Text, View } from 'react-native';

import {
  formatPurchaseDate,
  maximumPurchaseDate,
  purchaseDatePickerValue
} from '../../portfolio/purchaseDate';
import { colors, spacing } from '../../theme/theme';
import { Button } from '../ui/Button';

export function PurchaseDateField({
  editable = true,
  error,
  onChangeText,
  value
}: {
  editable?: boolean;
  error?: string | null;
  onChangeText: (value: string) => void;
  value: string;
}) {
  const [pickerVisible, setPickerVisible] = useState(false);
  const maximumDate = useMemo(() => maximumPurchaseDate(), [pickerVisible]);
  const selectedDate = purchaseDatePickerValue(value, maximumDate);

  function handleChange(event: DateTimePickerEvent, date?: Date) {
    if (Platform.OS !== 'ios') setPickerVisible(false);
    if (event.type === 'dismissed' || !date) return;
    onChangeText(formatPurchaseDate(date));
  }

  function closeIosPicker() {
    if (!value) onChangeText(formatPurchaseDate(selectedDate));
    setPickerVisible(false);
  }

  return (
    <View style={styles.wrapper}>
      <Text style={styles.label}>Purchase Date</Text>
      <Pressable
        accessibilityHint="Opens a calendar. Future dates are unavailable."
        accessibilityLabel={value ? `Purchase date, ${value}` : 'Choose purchase date'}
        accessibilityRole="button"
        accessibilityState={{ disabled: !editable, expanded: pickerVisible }}
        disabled={!editable}
        onPress={() => setPickerVisible(true)}
        style={({ pressed }) => [
          styles.field,
          error ? styles.errorField : null,
          pressed && editable ? styles.pressed : null,
          !editable ? styles.disabled : null
        ]}
      >
        <Text style={value ? styles.value : styles.placeholder}>
          {value || 'YYYY-MM-DD'}
        </Text>
        <Ionicons name="calendar-outline" color={colors.primary} size={21} />
      </Pressable>

      {error ? <Text style={styles.errorText}>{error}</Text> : null}

      {pickerVisible ? (
        <View style={styles.pickerPanel}>
          <DateTimePicker
            display={Platform.OS === 'ios' ? 'inline' : 'default'}
            maximumDate={maximumDate}
            mode="date"
            onChange={handleChange}
            value={selectedDate}
          />
          {Platform.OS === 'ios' ? (
            <Button
              title="Done"
              variant="secondary"
              onPress={closeIosPicker}
            />
          ) : null}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: { gap: spacing.sm },
  label: { color: colors.textSecondary, fontWeight: '700' },
  field: {
    minHeight: 52,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md,
    borderRadius: 15,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceAlt,
    paddingHorizontal: spacing.lg
  },
  errorField: { borderColor: colors.danger },
  pressed: { opacity: 0.72 },
  disabled: { opacity: 0.5 },
  value: { flex: 1, color: colors.text, fontSize: 15 },
  placeholder: { flex: 1, color: colors.muted, fontSize: 15 },
  errorText: { color: colors.danger, fontSize: 11, lineHeight: 16 },
  pickerPanel: {
    gap: spacing.sm,
    borderRadius: 15,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
    padding: spacing.sm,
    overflow: 'hidden'
  }
});
