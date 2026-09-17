import type { PortfolioReturnPoint } from '../../types/analytics';

export type ReturnViewRange = '1M' | '3M' | '6M' | '1Y' | 'ALL';

export const RETURN_VIEW_RANGES: ReturnViewRange[] = ['1M', '3M', '6M', '1Y', 'ALL'];

const RANGE_MONTHS: Record<Exclude<ReturnViewRange, 'ALL'>, number> = {
  '1M': 1,
  '3M': 3,
  '6M': 6,
  '1Y': 12,
};

function calendarCutoff(anchor: string, months: number): string | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(anchor);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const targetMonthIndex = year * 12 + month - 1 - months;
  const targetYear = Math.floor(targetMonthIndex / 12);
  const targetMonthIndexInYear = targetMonthIndex - targetYear * 12;
  const lastDay = new Date(Date.UTC(targetYear, targetMonthIndexInYear + 1, 0)).getUTCDate();
  return `${String(targetYear).padStart(4, '0')}-${String(targetMonthIndexInYear + 1).padStart(2, '0')}-${String(Math.min(day, lastDay)).padStart(2, '0')}`;
}

export function visibleReturnPoints(
  points: PortfolioReturnPoint[],
  viewRange: ReturnViewRange,
): PortfolioReturnPoint[] {
  if (viewRange === 'ALL' || !points.length) return points;
  const anchor = points[points.length - 1].date;
  const cutoff = calendarCutoff(anchor, RANGE_MONTHS[viewRange]);
  if (!cutoff) return points;
  return points.filter(point => point.date >= cutoff && point.date <= anchor);
}
