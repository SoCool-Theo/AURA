import { useState } from 'react';
import type { UserSettings } from '../../types/settings';
import { go } from '../../app/routes';
import { Icon } from '../ui/Icon';

type ProfileMenuProps = {
  settings: UserSettings;
};

export function ProfileMenu({ settings }: ProfileMenuProps) {
  const [open, setOpen] = useState(false);
  const initials = settings.name
    ?.split(/\s+/)
    .map((part) => part[0])
    .slice(0, 2)
    .join('')
    .toUpperCase() || 'YL';

  function openPage(path: string) {
    setOpen(false);
    go(path);
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
          <strong>{settings.name || 'Aura User'}</strong>
          <small>{settings.email || 'Portfolio owner'}</small>
          <button role="menuitem" onClick={() => openPage('settings')}>Settings</button>
          <button role="menuitem" onClick={() => openPage('watchlist')}>Watchlist</button>
          <button role="menuitem" onClick={() => openPage('learn')}>Learn</button>
        </div>
      )}
    </div>
  );
}
