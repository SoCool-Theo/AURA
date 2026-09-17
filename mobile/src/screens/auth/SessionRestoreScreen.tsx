import React, { useRef, useState } from 'react';
import { StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ScreenErrorState } from '../../components/ui/ErrorState';
import { colors } from '../../theme/theme';

export function SessionRestoreScreen({
  message,
  error: sessionFailure,
  onRetry,
  onSignOut
}: {
  message: string;
  error: unknown;
  onRetry: () => Promise<void>;
  onSignOut: () => Promise<void>;
}) {
  const pendingRef = useRef(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function perform(action: () => Promise<void>) {
    if (pendingRef.current) return;
    pendingRef.current = true;
    setPending(true);
    setError(null);
    try { await action(); }
    catch { setError('The session action could not be completed. Please retry.'); }
    finally { pendingRef.current = false; setPending(false); }
  }
  return (
    <SafeAreaView style={styles.safe}>
      <ScreenErrorState
        error={sessionFailure}
        message={error ?? message}
        onRetry={() => void perform(onRetry)}
        retryTitle={pending ? 'Please wait…' : 'Retry session'}
        onBack={() => void perform(onSignOut)}
        backTitle="Sign out"
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background }
});
