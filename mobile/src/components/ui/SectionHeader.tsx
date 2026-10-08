import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, spacing, typography } from '../../theme/theme';

export function SectionHeader({
  title,
  action,
  onPress
}: {
  title: string;
  action?: string;
  onPress?: () => void;
}) {
  return (
    <View style={styles.row}>
      <Text style={styles.title}>{title}</Text>
      {action ? (
        <Pressable
          accessibilityLabel={`${action} ${title}`}
          accessibilityRole="button"
          disabled={!onPress}
          hitSlop={6}
          onPress={onPress}
          style={styles.actionButton}
        >
          <Text style={styles.action}>{action}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: spacing.xl, marginBottom: spacing.md },
  title: { color: colors.text, ...typography.h2, flex: 1 },
  actionButton: { minHeight: 44, justifyContent: 'center', paddingHorizontal: spacing.sm },
  action: { color: colors.primary, fontSize: 12, fontWeight: '800' }
});
