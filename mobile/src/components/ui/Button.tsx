import React from 'react';
import { Pressable, StyleProp, StyleSheet, Text, ViewStyle } from 'react-native';
import { colors, spacing } from '../../theme/theme';

export function Button({
  title,
  onPress,
  variant = 'primary',
  style,
  disabled
}: {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  style?: StyleProp<ViewStyle>;
  disabled?: boolean;
}) {
  return (
    <Pressable
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.base,
        variant === 'primary' && styles.primary,
        variant === 'secondary' && styles.secondary,
        variant === 'danger' && styles.danger,
        variant === 'ghost' && styles.ghost,
        pressed && styles.pressed,
        disabled && styles.disabled,
        style
      ]}
    >
      <Text style={[
        styles.text,
        variant === 'secondary' && styles.secondaryText,
        variant === 'danger' && styles.dangerText,
        variant === 'ghost' && styles.ghostText
      ]}>
        {title}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: { minHeight: 48, borderRadius: 14, alignItems: 'center', justifyContent: 'center', paddingHorizontal: spacing.lg },
  primary: { backgroundColor: colors.primary },
  secondary: { backgroundColor: colors.surfaceAlt, borderWidth: 1, borderColor: colors.border },
  danger: { backgroundColor: colors.negativeBackground, borderWidth: 1, borderColor: colors.dangerBorder },
  ghost: { backgroundColor: 'transparent' },
  pressed: { opacity: 0.78 },
  disabled: { opacity: 0.4 },
  text: { color: colors.onPrimary, fontWeight: '900', fontSize: 14 },
  secondaryText: { color: colors.text },
  dangerText: { color: colors.danger },
  ghostText: { color: colors.primary }
});
