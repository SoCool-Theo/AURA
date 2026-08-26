import { useEffect, useState } from 'react';
import { go, routeFromHash } from '../app/routes';

export function useHashRoute() {
  const [route, setRoute] = useState(routeFromHash());

  useEffect(() => {
    const handleHashChange = () => setRoute(routeFromHash());

    window.addEventListener('hashchange', handleHashChange);
    if (!window.location.hash) go('dashboard');

    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  return route;
}
