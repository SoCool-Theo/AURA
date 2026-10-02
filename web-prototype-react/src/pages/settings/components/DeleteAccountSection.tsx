import { useRef, useState } from 'react';
import { deleteCurrentUserAccount } from '../../../api/authApi';
import { useAuth } from '../../../auth/useAuth';
import { Card } from '../../../components/ui/Card';
import { ConfirmationDialog } from '../../../components/ui/ConfirmationDialog';
import { Icon } from '../../../components/ui/Icon';
import styles from '../SettingsPage.module.css';

export function DeleteAccountSection({ disabled = false }: { disabled?: boolean }) {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
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
    setError(null);
    try {
      await deleteCurrentUserAccount({ current_password: password });
    } catch (failure) {
      setError(failure);
      pendingRef.current = false;
      setBusy(false);
      return;
    }
    // Deletion has succeeded; never report a logout/storage error as a failed delete.
    setDeleted(true);
    setOpen(false);
    setPassword('');
    try { logout(); } catch { /* AuthProvider clears authenticated UI in finally. */ }
    pendingRef.current = false;
    setBusy(false);
  }

  return (
    <>
      <Card className={styles.dangerSection}>
        <div className={styles.sectionHeading}>
          <span className={`${styles.sectionIcon} ${styles.dangerIcon}`}><Icon name="trash" size={19} /></span>
          <div><h2>Delete account</h2><p>Permanently remove your account, portfolios, holdings, analysis reports, saved simulations, and watchlist. This cannot be undone.</p></div>
        </div>
        <button type="button" className={styles.deleteAccountButton} disabled={disabled || busy || deleted || !user}
          onClick={() => { setPassword(''); setError(null); setOpen(true); }}>
          <Icon name="trash" size={16} />{deleted ? 'Account deleted' : 'Delete Account'}
        </button>
      </Card>
      {open && <ConfirmationDialog title="Delete account?"
        description="This permanently deletes your Aura account and all owned portfolios, holdings, analysis reports, saved simulations, and watchlist entries. It cannot be undone. Shared market data stays unchanged."
        subject={user?.email ?? ''} subjectLabel="ACCOUNT TO DELETE" confirmLabel="Delete Account"
        tone="danger" busy={busy} error={error} confirmDisabled={password.length < 8 || disabled}
        onCancel={cancel} onConfirm={() => void confirm()}>
        <div className={styles.passwordFields}>
          <label>Current password<input type="password" autoComplete="current-password" value={password}
            disabled={busy} onChange={event => setPassword(event.target.value)} /></label>
        </div>
        <p className={styles.fieldNote}>Enter your current password to confirm permanent deletion.</p>
      </ConfirmationDialog>}
    </>
  );
}
