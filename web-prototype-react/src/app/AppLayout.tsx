import type { ReactNode } from 'react';
import { TopNavigation } from '../components/navigation/TopNavigation';
import type { UserSettings } from '../types/settings';
import type { AppRoute } from './routes';

type AppLayoutProps = {
  children: ReactNode;
  route: AppRoute;
  settings: UserSettings;
};

export function AppLayout({ children, route, settings }: AppLayoutProps) {
  return (
    <div className="app-shell">
      <TopNavigation route={route} settings={settings} />
      <main className="main-area">
        {children}
      </main>
    </div>
  );
}
