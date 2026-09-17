import React from 'react';
import { Pressable, StyleSheet, type ColorValue } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { colors } from '../../theme/colors';

export function BackHeaderButton({
  onPress,
  label = 'Go back',
  color = colors.text
}: {
  onPress: () => void;
  label?: string;
  color?: ColorValue;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      hitSlop={8}
      onPress={onPress}
      style={({ pressed }) => [styles.button, pressed && styles.pressed]}
    >
      <Ionicons name="arrow-back" color={color} size={23} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    minWidth: 44,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center'
  },
  pressed: { opacity: 0.6 }
});
