import type { MarketDataStatusResponse } from '../types/marketData';

export function marketDataPresentation(status: MarketDataStatusResponse | null, unavailable: boolean, symbols: string[]) {
  if (unavailable) return { tone: 'warning' as const, title: 'Daily data status unavailable', detail: 'Saved prices remain available. Refresh to check again.' };
  if (!status) return { tone: 'muted' as const, title: 'Checking daily data…', detail: 'Saved prices, not live quotes.' };
  // Scope freshness to displayed instruments, not unrelated assets in the universe.
  const observations = symbols.map(symbol => status.observations.find(item => item.symbol === symbol));
  const missing = observations.some(item => !item?.latest_price_date);
  const stale = observations.some(item => !item?.is_current);
  const title = !symbols.length ? 'Daily saved prices' : missing ? 'Some saved prices are missing' : stale ? 'Some saved prices are outdated' : 'Daily saved prices are current';
  const updateProblem = status.worker_status !== 'online' || status.last_run_status === 'partial' || status.last_run_status === 'failed';
  const tone = missing || stale || updateProblem ? 'warning' as const : !symbols.length ? 'muted' as const : 'success' as const;
  const operation = status.worker_status === 'offline' ? 'Automatic updater offline.'
    : status.worker_status === 'unknown' ? 'Automatic updater not connected.'
    : 'Automatic updater connected.';
  const outcome = status.last_run_status === 'partial' ? ' Latest refresh was partial.'
    : status.last_run_status === 'failed' ? ' Latest refresh failed.'
    : status.last_run_status === 'running' ? ' Last attempt is marked in progress.'
    : '';
  return { tone, title, detail: operation + outcome + ' Checked ' + new Date(status.checked_at).toLocaleString() + '. Not live quotes.' };
}
