import { formatRatioPercent } from '../report/reportFormatting';

export type ReturnViewRange = '1M' | '3M' | '6M' | '1Y' | 'ALL';
export type DashboardRange = ReturnViewRange;

export const RETURN_VIEW_RANGES: ReturnViewRange[] = ['1M', '3M', '6M', '1Y', 'ALL'];

export function dashboardPercent(value: number | null | undefined): string {
  return value == null ? 'N/A' : formatRatioPercent(value);
}

// Viewport filtering only. Report metrics and returned observations are unchanged.
export function filterReturnPoints<T extends { date: string }>(
  points: T[],
  range: ReturnViewRange
): T[] {
  if (!points.length || range === 'ALL') return points;
  const latest = points.reduce((date, point) => point.date > date ? point.date : date, points[0].date);
  const end = new Date(`${latest}T00:00:00Z`);
  const months = { '1M': 1, '3M': 3, '6M': 6, '1Y': 12 }[range];
  const start = new Date(Date.UTC(end.getUTCFullYear(), end.getUTCMonth() - months, 1));
  const lastDay = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth() + 1, 0)).getUTCDate();
  start.setUTCDate(Math.min(end.getUTCDate(), lastDay));
  const first = start.toISOString().slice(0, 10);
  return points.filter((point) => point.date >= first && point.date <= latest);
}

export const filterDashboardReturns = filterReturnPoints;
