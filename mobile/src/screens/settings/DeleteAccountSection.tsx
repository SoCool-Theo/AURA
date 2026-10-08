import React, { useRef, useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';
import { authApi } from '../../api/authApi';
import { ApiError } from '../../api/apiClient';
import { apiErrorPresentation } from '../../api/apiErrorPresentation';
import { useAuth } from '../../auth/useAuth';
import { Button } from '../../components/ui/Button';
import { ConfirmationDialog } from '../../components/ui/ConfirmationDialog';
import { colors, spacing } from '../../theme/theme';

export function DeleteAccountSection({ disabled = false, onBusyChange }: {
  disabled?: boolean;
  onBusyChange: (busy: boolean) => void;
}) {
  const { user, signOut } = useAuth();
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleted, setDeleted] = useState(false);
  const pendingRef = useRef(false);

  function cancel() {
    if (pendingRef.current) return;
    setOpen(false);
    setPassword('');
    setError(null);
  }

  async function confirm() {
    if (!open || !user || disabled || deleted || pendingRef.current || password.length < 8) return;
    pendingRef.current = true;
    setBusy(true);
    onBusyChange(true);
    setError(null);
    try {
      await authApi.deleteAccount({ current_password: password });
    } catch (failure) {
      setError(failure instanceof ApiError && failure.status === 403
        ? 'The current password is incorrect.'
        : apiErrorPresentation(failure, { fallbackMessage: 'Aura could not delete your account. Please try again.' }).message);
      pendingRef.current = false;
      setBusy(false);
      onBusyChange(false);
      return;
    }
    // The server already deleted the account. Session cleanup cannot undo it.
    setDeleted(true);
    setOpen(false);
    setPassword('');
    try { await signOut(); } catch { /* AuthProvider exposes secure-storage cleanup failures. */ }
    pendingRef.current = false;
    setBusy(false);
    onBusyChange(false);
  }

  return (
    <View style={styles.section}>
      <Text style={styles.title}>Delete account</Text>
      <Text style={styles.description}>Permanently remove your account, portfolios, holdings, analysis reports, saved simulations, and watchlist. This cannot be undone.</Text>
      <Button title={deleted ? 'Account deleted' : 'Delete Account'} variant="danger"
        disabled={disabled || busy || deleted || !user} style={styles.button}
        onPress={() => { setPassword(''); setError(null); setOpen(true); }} />
      <ConfirmationDialog visible={open} title="Delete account?"
        description="This permanently deletes your Aura account and all owned portfolios, holdings, analysis reports, saved simulations, and watchlist entries. It cannot be undone. Shared market data stays unchanged."
        subject={user?.email ?? ''} subjectLabel="ACCOUNT TO DELETE" confirmLabel="Delete Account"
        tone="danger" busy={busy} errorMessage={error} confirmDisabled={password.length < 8 || disabled}
        onCancel={cancel} onConfirm={() => void confirm()}>
        <Text style={styles.passwordLabel}>Current password</Text>
        <TextInput accessibilityLabel="Current password to delete account" value={password}
          onChangeText={setPassword} secureTextEntry autoCapitalize="none" autoCorrect={false}
          textContentType="password" autoComplete="current-password" editable={!busy}
          placeholder="Current password" placeholderTextColor={colors.muted} style={styles.input} />
      </ConfirmationDialog>
    </View>
  );
}

const styles = StyleSheet.create({
  section: { marginTop: spacing.xl, padding: spacing.lg, borderRadius: 16, borderWidth: 1, borderColor: colors.dangerBorder, backgroundColor: colors.negativeBackground },
  title: { color: colors.danger, fontSize: 16, fontWeight: '800' },
  description: { marginTop: spacing.sm, color: colors.textSecondary, fontSize: 12, lineHeight: 18 },
  button: { marginTop: spacing.md },
  passwordLabel: { marginTop: spacing.lg, color: colors.text, fontSize: 12, fontWeight: '700' },
  input: { marginTop: spacing.sm, padding: spacing.md, borderWidth: 1, borderColor: colors.dangerBorder, borderRadius: 12, backgroundColor: '#150a10', color: colors.text, fontSize: 14 },
});
