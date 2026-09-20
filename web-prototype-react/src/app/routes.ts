export type AppRoute = {
  page: string;
  id?: string;
  reportId?: string;
  contextId?: string;
};

export function routeFromHash(): AppRoute {
  const raw = window.location.hash.replace(/^#\/?/, '') || 'dashboard';
  const [page, id, reportId, contextId] = raw.split('/');

  return { page, id, reportId, contextId };
}

export function go(path: string): void {
  window.location.hash = `#/${path}`;
}

export function replace(path: string): void {
  window.history.replaceState(null, '', `#/${path}`);
}
