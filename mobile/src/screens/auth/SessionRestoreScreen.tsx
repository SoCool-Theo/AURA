import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { colors, spacing } from '../../theme/theme';

export function SessionRestoreScreen({
  message,
  onRetry,
  onSignOut
}: {
  message: string;
  onRetry: () => Promise<void>;
  onSignOut: () => Promise<void>;
}) {
  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.content}>
        <Card style={styles.card}>
          <Text style={styles.title}>Session verification unavailable</Text>
          <Text style={styles.message}>{message}</Text>
          <Text style={styles.note}>
            Retry without deleting your saved session, or sign out to remove it from this device.
          </Text>
          <View style={styles.actions}>
            <Button title="Retry" onPress={() => void onRetry()} />
            <Button
              title="Sign out"
              variant="secondary"
              onPress={() => void onSignOut()}
            />
          </View>
        </Card>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { flex: 1, justifyContent: 'center', padding: spacing.xl },
  card: { gap: spacing.md },
  title: { color: colors.text, fontSize: 20, fontWeight: '900' },
  message: { color: colors.textSecondary, fontSize: 13, lineHeight: 20 },
  note: { color: colors.muted, fontSize: 11, lineHeight: 17 },
  actions: { gap: spacing.md, marginTop: spacing.sm }
});
