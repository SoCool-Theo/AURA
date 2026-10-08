import type { ReactNode } from 'react';
import { TopNavigation } from '../components/navigation/TopNavigation';
import type { AppRoute } from './routes';

type AppLayoutProps = {
  children: ReactNode;
  route: AppRoute;
};

export function AppLayout({ children, route }: AppLayoutProps) {
  return (
    <div className="app-shell">
      <TopNavigation route={route} />
      <main className="main-area">
        {children}
      </main>
    </div>
  );
}
