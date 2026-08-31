import { ApiError } from '../../api/apiClient';
import type { SimulationHistoryDetailResponse, SimulationRunResult } from '../../types/simulation';

export function formatPercent(value: number, fractionDigits = 2): string {
  return `${(value * 100).toFixed(fractionDigits)}%`;
}

export function formatNumber(value: number | null, fractionDigits = 2): string {
  return value === null ? 'N/A' : value.toFixed(fractionDigits);
}

export function formatTimestamp(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

export function simulationErrorMessage(error: unknown, fallback: string): string {
  if (!(error instanceof ApiError)) return fallback;
  if (typeof error.detail === 'string' && error.detail) return error.detail;
  if (Array.isArray(error.detail)) {
    const messages = error.detail.flatMap(item => (
      item && typeof item === 'object' && !Array.isArray(item) && typeof item.msg === 'string'
        ? [item.msg]
        : []
    ));
    if (messages.length) return messages.join('. ');
  }
  return error.message || fallback;
}

export function historyDetailToRunResult(detail: SimulationHistoryDetailResponse): SimulationRunResult {
  return { type: detail.simulation_type, response: detail.result } as SimulationRunResult;
}
