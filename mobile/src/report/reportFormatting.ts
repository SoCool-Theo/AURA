import type { RiskLevel } from '../types/analytics';

export function formatRatioPercent(
  value: number,
  fractionDigits = 2
): string {
  return `${(value * 100).toFixed(fractionDigits)}%`;
}

export function formatAnalysisNumber(
  value: number | null,
  fractionDigits = 2
): string {
  return value === null ? 'N/A' : value.toFixed(fractionDigits);
}

export function formatReportTimestamp(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

export function riskTone(
  level: RiskLevel
): 'success' | 'warning' | 'danger' {
  if (level === 'Low') return 'success';
  if (level === 'Moderate') return 'warning';
  return 'danger';
}
