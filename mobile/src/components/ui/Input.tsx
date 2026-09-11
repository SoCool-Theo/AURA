import { Ionicons } from '@expo/vector-icons';
import React, { useState } from 'react';
import {
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  TextInputProps,
  View
} from 'react-native';
import { colors, spacing } from '../../theme/theme';

type InputProps = TextInputProps & { label?: string };

export function Input({
  editable,
  label,
  secureTextEntry,
  style,
  ...props
}: InputProps) {
  const [passwordVisible, setPasswordVisible] = useState(false);
  const showsPasswordToggle = secureTextEntry === true;
  const accessibilityFieldName = label?.toLowerCase() ?? 'password';

  return (
    <View style={styles.wrapper}>
      {label ? <Text style={styles.label}>{label}</Text> : null}
      <View style={styles.inputWrapper}>
        <TextInput
          style={[
            styles.input,
            showsPasswordToggle && styles.passwordInput,
            style
          ]}
          placeholderTextColor={colors.muted}
          autoCapitalize="none"
          editable={editable}
          secureTextEntry={showsPasswordToggle && !passwordVisible}
          {...props}
        />
        {showsPasswordToggle ? (
          <Pressable
            accessibilityLabel={`${passwordVisible ? 'Hide' : 'Show'} ${accessibilityFieldName}`}
            accessibilityRole="button"
            accessibilityState={{ disabled: editable === false }}
            disabled={editable === false}
            hitSlop={4}
            onPress={() => setPasswordVisible((visible) => !visible)}
            style={({ pressed }) => [
              styles.visibilityButton,
              pressed && styles.visibilityButtonPressed
            ]}
          >
            <Ionicons
              color={editable === false ? colors.muted : colors.textSecondary}
              name={passwordVisible ? 'eye-off-outline' : 'eye-outline'}
              size={21}
            />
          </Pressable>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: { gap: spacing.sm },
  label: { color: colors.textSecondary, fontWeight: '700' },
  inputWrapper: { position: 'relative' },
  input: {
    minHeight: 52,
    borderRadius: 15,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceAlt,
    color: colors.text,
    paddingHorizontal: spacing.lg,
    fontSize: 15
  },
  passwordInput: { paddingRight: 58 },
  visibilityButton: {
    position: 'absolute',
    top: 4,
    right: 4,
    bottom: 4,
    width: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 12
  },
  visibilityButtonPressed: { opacity: 0.65 }
});
