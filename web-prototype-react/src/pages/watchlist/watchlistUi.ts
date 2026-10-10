import { ApiError } from '../../api/apiClient';

const usdFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 2,
});

export function formatWatchlistPrice(value: number | null): string {
  return value === null ? '—' : usdFormatter.format(value);
}

export function formatWatchlistPercent(value: number | null): string {
  if (value === null) return '—';
  return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`;
}

export function formatWatchlistDate(value: string | null): string {
  if (value === null) return '—';
  const parsed = new Date(`${value}T00:00:00`);
  return Number.isNaN(parsed.getTime())
    ? value
    : parsed.toLocaleDateString(undefined, { dateStyle: 'medium' });
}

export function watchlistErrorMessage(error: unknown, action: 'add' | 'remove'): string {
  if (!(error instanceof ApiError)) {
    return action === 'add'
      ? 'Unable to add this asset. Please try again.'
      : 'Unable to remove this asset. Please try again.';
  }
  if (error.status === 409) return 'This asset is already in your Watchlist.';
  if (error.status === 422) return 'Choose one of Aura’s supported assets.';
  if (error.status === 404) return 'This asset is no longer in your Watchlist. Refresh and try again.';
  if (error.kind === 'network') return 'Cannot connect to Aura. Check your connection and try again.';
  return action === 'add'
    ? 'Aura could not add this asset. Please try again.'
    : 'Aura could not remove this asset. Please try again.';
}
