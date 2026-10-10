import { useRef, useState } from 'react';
import { go } from '../../app/routes';
import { accountDisplayName, accountInitials } from '../../auth/accountIdentity';
import { useAuth } from '../../auth/useAuth';
import { Icon } from '../ui/Icon';
import { ConfirmationDialog } from '../ui/ConfirmationDialog';

export function ProfileMenu() {
  const [open, setOpen] = useState(false);
  const [confirmingSignOut, setConfirmingSignOut] = useState(false);
  const [signOutPending, setSignOutPending] = useState(false);
  const [signOutError, setSignOutError] = useState<unknown>(null);
  const confirmationRef = useRef(false);
  const pendingRef = useRef(false);
  const { logout, user } = useAuth();
  const displayName = accountDisplayName(user);
  const initials = accountInitials(user);

  function openPage(path: string) {
    setOpen(false);
    go(path);
  }

  function requestSignOut() {
    setOpen(false);
    confirmationRef.current = true;
    setSignOutError(null);
    setConfirmingSignOut(true);
  }

  function cancelSignOut() {
    if (pendingRef.current) return;
    confirmationRef.current = false;
    setConfirmingSignOut(false);
    setSignOutError(null);
  }

  function signOut() {
    if (!confirmationRef.current || pendingRef.current) return;
    pendingRef.current = true;
    setSignOutPending(true);
    setSignOutError(null);
    try {
      logout();
      confirmationRef.current = false;
      setConfirmingSignOut(false);
      go('login');
    } catch {
      setSignOutError(new Error('Aura could not remove the saved session. Please retry sign out.'));
    } finally {
      pendingRef.current = false;
      setSignOutPending(false);
    }
  }

  return (
    <div className="profile-menu-wrap">
      <button
        className="profile-trigger"
        onClick={() => setOpen((value) => !value)}
        aria-label="Open user menu"
        aria-expanded={open}
        aria-haspopup="menu"
      >
        <span className="avatar">{initials}</span>
        <span className="chevron"><Icon name="chevron-down" size={17}/></span>
      </button>
      {open && (
        <div className="profile-menu" role="menu">
          <strong title={displayName}>{displayName}</strong>
          <small title={user?.email}>
            {user?.display_name ? user.email : 'Authenticated Aura account'}
          </small>
          <button role="menuitem" onClick={() => openPage('settings')}>Settings</button>
          <button role="menuitem" onClick={() => openPage('watchlist')}>Watchlist</button>
          <button role="menuitem" onClick={() => openPage('learn')}>Learn</button>
          <button className="profile-sign-out" role="menuitem" onClick={requestSignOut}>Sign out</button>
        </div>
      )}
      {confirmingSignOut && <ConfirmationDialog title="Sign out?"
        description="You'll need to sign in again to access Aura. Your account, portfolios, reports, and saved simulations will not be deleted."
        subject={user?.email ?? displayName} subjectLabel="SIGNED-IN ACCOUNT" confirmLabel="Sign out"
        tone="danger" iconName="logout" busy={signOutPending} error={signOutError}
        onCancel={cancelSignOut} onConfirm={signOut} />}
    </div>
  );
}
