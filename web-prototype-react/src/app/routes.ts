export type AppRoute = {
  page: string;
  id?: string;
  reportId?: string;
};

export function routeFromHash(): AppRoute {
  const raw = window.location.hash.replace(/^#\/?/, '') || 'dashboard';
  const [page, id, reportId] = raw.split('/');

  return { page, id, reportId };
}

export function go(path: string): void {
  window.location.hash = `#/${path}`;
}
