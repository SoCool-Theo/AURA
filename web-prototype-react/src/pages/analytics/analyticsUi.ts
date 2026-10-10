import { ApiError } from '../../api/apiClient';
import type { RiskLevel } from '../../types/analytics';

// Presentation only: use the classification saved by the backend, not score thresholds.
export function riskColor(level?: RiskLevel): string {
  if (level === 'Low') return 'var(--green-primary)';
  if (level === 'Moderate') return 'var(--amber-primary)';
  if (level === 'High' || level === 'Very High') return 'var(--red-bright)';
  return 'var(--text-muted)';
}

export function formatPercent(value: number, fractionDigits = 2): string {
  return `${(value * 100).toFixed(fractionDigits)}%`;
}

export function formatNumber(
  value: number | null,
  fractionDigits = 2,
): string {
  return value === null ? 'N/A' : value.toFixed(fractionDigits);
}

export function formatReportTimestamp(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

export function analysisErrorMessage(error: unknown, fallback: string): string {
  if (!(error instanceof ApiError)) return fallback;
  if (error.status === 503) {
    return 'Required current market or currency data is unavailable or stale. Analysis will be available after the market data refresh completes; no report was saved.';
  }
  if (typeof error.detail === 'string' && error.detail) return error.detail;

  if (Array.isArray(error.detail)) {
    const messages = error.detail.flatMap(item => {
      if (
        item
        && typeof item === 'object'
        && !Array.isArray(item)
        && typeof item.msg === 'string'
      ) {
        return [item.msg];
      }
      return [];
    });
    if (messages.length) return messages.join('. ');
  }

  return error.message || fallback;
}
