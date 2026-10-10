import React from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { colors, spacing } from '../../theme/theme';

export function LoadingState({ message = 'Loading…' }: { message?: string }) {
  return (
    <View accessibilityLabel={message} accessibilityRole="progressbar" style={styles.wrapper}>
      <ActivityIndicator color={colors.primary} size="large" />
      <Text style={styles.text}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: spacing.md, backgroundColor: colors.background },
  text: { color: colors.textSecondary }
});
