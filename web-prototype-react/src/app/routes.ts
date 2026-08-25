export type AppRoute = {
  page: string;
  id?: string;
};

export function routeFromHash(): AppRoute {
  const raw = window.location.hash.replace(/^#\/?/, '') || 'dashboard';
  const [page, id] = raw.split('/');

  return { page, id };
}

export function go(path: string): void {
  window.location.hash = `#/${path}`;
}
