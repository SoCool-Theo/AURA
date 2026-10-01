import { useState } from 'react';
import { go } from '../../app/routes';
import { accountDisplayName, accountInitials } from '../../auth/accountIdentity';
import { useAuth } from '../../auth/useAuth';
import { Icon } from '../ui/Icon';

export function ProfileMenu() {
  const [open, setOpen] = useState(false);
  const { logout, user } = useAuth();
  const displayName = accountDisplayName(user);
  const initials = accountInitials(user);

  function openPage(path: string) {
    setOpen(false);
    go(path);
  }

  function signOut() {
    setOpen(false);
    logout();
    go('login');
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
          <button className="profile-sign-out" role="menuitem" onClick={signOut}>Sign out</button>
        </div>
      )}
    </div>
  );
}
