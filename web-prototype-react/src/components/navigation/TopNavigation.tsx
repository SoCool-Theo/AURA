import { navItems } from '../../app/navigation';
import { go, type AppRoute } from '../../app/routes';
import { Icon } from '../ui/Icon';
import { ProfileMenu } from './ProfileMenu';
import { useNotificationBadge } from '../../notifications/useNotifications';

type TopNavigationProps = {
  route: AppRoute;
};

export function TopNavigation({ route }: TopNavigationProps) {
  const unread = useNotificationBadge();
  const isActive = (key: string) => (
    route.page === key
    || (key === 'portfolios' && ['portfolio', 'create'].includes(route.page))
    || (key === 'reports' && route.page === 'asset')
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
          <button className="nav-action" aria-label="Search unavailable" title="Search is not available yet" disabled><Icon name="search" size={21}/></button>
          <button className="nav-action notification-button" aria-label={unread == null ? 'Open notifications' : `Notifications, ${unread} unread`} title="Open notifications" onClick={() => go('notifications')}>
            <Icon name="bell" size={21}/>
            {unread != null && unread > 0 && <span className="notification-dot" aria-hidden="true" />}
          </button>
          <ProfileMenu />
        </div>
      </div>
    </header>
  );
}
