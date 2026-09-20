import { ApiError } from '../../api/apiClient';

export function formatPercent(value: number, fractionDigits = 2): string {
  return `${(value * 100).toFixed(fractionDigits)}%`;
}

export function portfolioReturnAxisTicks(
  domainMin: number,
  domainMax: number,
  tickCount = 5,
): number[] {
  const interval = (domainMax - domainMin) / Math.max(tickCount - 1, 1);
  const ticks = Array.from(
    { length: tickCount },
    (_, index) => domainMax - interval * index,
  );

  if (domainMin <= 0 && domainMax >= 0) {
    let nearestZeroIndex = 0;
    for (let index = 1; index < ticks.length; index += 1) {
      if (Math.abs(ticks[index]) < Math.abs(ticks[nearestZeroIndex])) {
        nearestZeroIndex = index;
      }
    }
    ticks[nearestZeroIndex] = 0;
  }

  return ticks.sort((left, right) => right - left);
}

export function formatPortfolioReturnTick(value: number, domainSpan: number): string {
  const percentSpan = domainSpan * 100;
  const fractionDigits = percentSpan < 1 ? 2 : percentSpan < 10 ? 1 : 0;
  const percent = value * 100;
  const zeroThreshold = 0.5 * 10 ** -fractionDigits;
  const normalizedPercent = Math.abs(percent) < zeroThreshold ? 0 : percent;
  return `${normalizedPercent.toFixed(fractionDigits)}%`;
}

export function formatTimestamp(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

export function dashboardErrorMessage(error: unknown, fallback: string): string {
  if (!(error instanceof ApiError)) return fallback;
  if (typeof error.detail === 'string' && error.detail) return error.detail;
  return error.message || fallback;
}
