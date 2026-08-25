import { navItems } from '../../app/navigation';
import { go, type AppRoute } from '../../app/routes';
import type { UserSettings } from '../../types/settings';
import { Icon } from '../ui/Icon';
import { ProfileMenu } from './ProfileMenu';

type TopNavigationProps = {
  route: AppRoute;
  settings: UserSettings;
};

export function TopNavigation({ route, settings }: TopNavigationProps) {
  const isActive = (key: string) => (
    route.page === key
    || (key === 'portfolios' && ['portfolio', 'create'].includes(route.page))
  );

  return (
    <header className="top-nav">
      <div className="top-nav-inner">
        <button className="brand" onClick={() => go('dashboard')} aria-label="Go to dashboard">
          <span className="brand-mark">A</span><span>AURA</span>
        </button>
        <nav className="nav-list" aria-label="Primary navigation">
          {navItems.map(([key, icon, label]) => {
            const active = isActive(key);
            return (
              <button
                key={key}
                className={`nav-item ${active ? 'active' : ''}`}
                aria-current={active ? 'page' : undefined}
                onClick={() => go(key)}
              >
                <span className="nav-icon"><Icon name={icon} size={18}/></span>
                <span>{label}</span>
              </button>
            );
          })}
        </nav>
        <div className="top-nav-actions">
          <button className="nav-action" aria-label="Search"><Icon name="search" size={21}/></button>
          <button className="nav-action notification-button" aria-label="Notifications">
            <Icon name="bell" size={21}/><span className="notification-dot" aria-hidden="true" />
          </button>
          <ProfileMenu settings={settings} />
        </div>
      </div>
    </header>
  );
}
