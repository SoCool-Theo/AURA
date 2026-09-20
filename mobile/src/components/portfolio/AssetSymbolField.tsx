import { Ionicons } from '@expo/vector-icons';
import React, { useEffect, useState } from 'react';
import {
  Keyboard,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  type TextInputProps,
  View
} from 'react-native';

import { supportedAssets } from '../../portfolio/supportedAssetSymbols';
import { colors, spacing } from '../../theme/theme';

type AssetSymbolFieldProps = Omit<
  TextInputProps,
  'onChangeText' | 'value'
> & {
  error?: string | null;
  onChangeText: (value: string) => void;
  value: string;
};

export function AssetSymbolField({
  accessibilityLabel,
  editable = true,
  error,
  onChangeText,
  placeholder = 'AAPL',
  style,
  value,
  ...props
}: AssetSymbolFieldProps) {
  const [pickerVisible, setPickerVisible] = useState(false);
  const normalizedValue = value.trim().toUpperCase();

  useEffect(() => {
    if (!editable) setPickerVisible(false);
  }, [editable]);

  function openPicker() {
    if (!editable) return;
    Keyboard.dismiss();
    setPickerVisible(true);
  }

  function chooseSymbol(symbol: string) {
    onChangeText(symbol);
    setPickerVisible(false);
  }

  return (
    <>
      <View style={[styles.field, error ? styles.errorField : null]}>
        <TextInput
          accessibilityLabel={accessibilityLabel ?? 'Asset symbol'}
          accessibilityState={{ disabled: !editable }}
          autoCapitalize="characters"
          autoCorrect={false}
          editable={editable}
          onChangeText={(nextValue) => onChangeText(nextValue.toUpperCase())}
          placeholder={placeholder}
          placeholderTextColor={colors.muted}
          style={[styles.input, style]}
          value={value}
          {...props}
        />
        <Pressable
          accessibilityLabel="Choose a supported asset symbol"
          accessibilityRole="button"
          accessibilityState={{ disabled: !editable, expanded: pickerVisible }}
          disabled={!editable}
          hitSlop={4}
          onPress={openPicker}
          style={({ pressed }) => [
            styles.pickerButton,
            pressed && styles.pickerButtonPressed
          ]}
        >
          <Ionicons
            color={editable ? colors.primary : colors.muted}
            name="chevron-down"
            size={20}
          />
        </Pressable>
      </View>
      {error ? <Text style={styles.errorText}>{error}</Text> : null}

      <Modal
        animationType="fade"
        onRequestClose={() => setPickerVisible(false)}
        statusBarTranslucent
        transparent
        visible={pickerVisible}
      >
        <View style={styles.backdrop}>
          <Pressable
            accessibilityLabel="Close asset symbol picker"
            accessibilityRole="button"
            onPress={() => setPickerVisible(false)}
            style={StyleSheet.absoluteFill}
          />
          <View accessibilityViewIsModal style={styles.menu}>
            <View style={styles.menuHeader}>
              <View style={styles.menuHeading}>
                <Text style={styles.menuTitle}>Choose asset symbol</Text>
                <Text style={styles.menuSubtitle}>
                  Aura’s 17 currently supported market-data symbols
                </Text>
              </View>
              <Pressable
                accessibilityLabel="Close asset symbol picker"
                accessibilityRole="button"
                hitSlop={4}
                onPress={() => setPickerVisible(false)}
                style={({ pressed }) => [
                  styles.closeButton,
                  pressed && styles.pickerButtonPressed
                ]}
              >
                <Ionicons color={colors.text} name="close" size={20} />
              </Pressable>
            </View>

            <ScrollView
              contentContainerStyle={styles.optionsContent}
              keyboardShouldPersistTaps="handled"
              nestedScrollEnabled
              showsVerticalScrollIndicator
              style={styles.options}
            >
              {supportedAssets.map((asset) => {
                const selected = asset.symbol === normalizedValue;
                return (
                  <Pressable
                    accessibilityLabel={`${asset.symbol}, ${asset.name}`}
                    accessibilityRole="radio"
                    accessibilityState={{ selected }}
                    key={asset.symbol}
                    onPress={() => chooseSymbol(asset.symbol)}
                    style={({ pressed }) => [
                      styles.option,
                      selected && styles.optionSelected,
                      pressed && styles.optionPressed
                    ]}
                  >
                    <View style={styles.optionCopy}>
                      <Text style={[
                        styles.optionText,
                        selected && styles.optionTextSelected
                      ]}>
                        {asset.symbol}
                      </Text>
                      <Text numberOfLines={1} style={styles.optionName}>— {asset.name}</Text>
                    </View>
                    {selected ? (
                      <Ionicons color={colors.primary} name="checkmark" size={19} />
                    ) : null}
                  </Pressable>
                );
              })}
            </ScrollView>

            <Text style={styles.menuNote}>
              You can close this list and type a symbol manually.
            </Text>
          </View>
        </View>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  field: { position: 'relative' },
  errorField: { borderRadius: 14, borderWidth: 1, borderColor: colors.danger },
  errorText: { color: colors.danger, fontSize: 11, lineHeight: 16, marginTop: 4 },
  input: {
    minHeight: 48,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceAlt,
    color: colors.text,
    paddingLeft: spacing.md,
    paddingRight: 52,
    fontWeight: '800'
  },
  pickerButton: {
    position: 'absolute',
    top: 2,
    right: 2,
    bottom: 2,
    width: 44,
    borderRadius: 11,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.surfaceElevated
  },
  pickerButtonPressed: { opacity: 0.65 },
  backdrop: {
    flex: 1,
    justifyContent: 'center',
    backgroundColor: 'rgba(0,0,0,0.62)',
    padding: spacing.xl
  },
  menu: {
    maxHeight: 420,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
    padding: spacing.lg
  },
  menuHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    marginBottom: spacing.md
  },
  menuHeading: { flex: 1 },
  menuTitle: { color: colors.text, fontSize: 18, fontWeight: '900' },
  menuSubtitle: {
    color: colors.textSecondary,
    fontSize: 11,
    lineHeight: 16,
    marginTop: spacing.xs
  },
  closeButton: {
    width: 44,
    height: 44,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.surfaceAlt
  },
  options: {
    flexGrow: 0,
    maxHeight: 264,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.backgroundSoft
  },
  optionsContent: { padding: spacing.sm, gap: spacing.xs },
  option: {
    minHeight: 44,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderRadius: 10,
    paddingHorizontal: spacing.md
  },
  optionSelected: {
    borderWidth: 1,
    borderColor: colors.primary,
    backgroundColor: colors.selectedBackground
  },
  optionPressed: { backgroundColor: colors.surfaceElevated },
  optionCopy: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  optionText: { color: colors.textSecondary, fontSize: 14, fontWeight: '800' },
  optionTextSelected: { color: colors.primary },
  optionName: { flex: 1, color: colors.muted, fontSize: 11 },
  menuNote: {
    color: colors.muted,
    fontSize: 10,
    lineHeight: 15,
    marginTop: spacing.md
  }
});
