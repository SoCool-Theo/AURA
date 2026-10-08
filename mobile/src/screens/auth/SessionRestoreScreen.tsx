import React, { useRef, useState } from 'react';
import { StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ScreenErrorState } from '../../components/ui/ErrorState';
import { ConfirmationDialog } from '../../components/ui/ConfirmationDialog';
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
  const [confirmingSignOut, setConfirmingSignOut] = useState(false);
  const confirmationRef = useRef(false);
  async function perform(action: () => Promise<void>) {
    if (pendingRef.current) return;
    pendingRef.current = true;
    setPending(true);
    setError(null);
    try { await action(); return true; }
    catch { setError('The session action could not be completed. Please retry.'); return false; }
    finally { pendingRef.current = false; setPending(false); }
  }
  async function confirmSignOut() {
    if (!confirmationRef.current || pendingRef.current) return;
    if (await perform(onSignOut)) {
      confirmationRef.current = false;
      setConfirmingSignOut(false);
    }
  }
  return (
    <SafeAreaView style={styles.safe}>
      <ScreenErrorState
        error={sessionFailure}
        message={error ?? message}
        onRetry={() => void perform(onRetry)}
        retryTitle={pending ? 'Please wait…' : 'Retry session'}
        onBack={() => {
          if (pendingRef.current) return;
          confirmationRef.current = true;
          setError(null);
          setConfirmingSignOut(true);
        }}
        backTitle="Sign out"
      />
      <ConfirmationDialog visible={confirmingSignOut} title="Sign out?"
        description="Remove the saved session from this device and return to sign in. Your account and saved portfolio data will not be deleted."
        subject="This device" subjectLabel="SAVED SESSION" confirmLabel="Sign out"
        tone="danger" iconName="log-out-outline" busy={pending} errorMessage={error}
        onCancel={() => {
          if (pendingRef.current) return;
          confirmationRef.current = false;
          setConfirmingSignOut(false);
          setError(null);
        }} onConfirm={() => void confirmSignOut()} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background }
});
