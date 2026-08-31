import { ApiError } from '../../api/apiClient';

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
