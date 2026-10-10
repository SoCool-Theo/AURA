import type { PortfolioAnalysisResponse } from '../types/analytics';
import type { HistoricalScenarioTrajectoryPoint } from '../types/simulation';

export function formatSimulationPercent(
  value: number,
  fractionDigits = 2
): string {
  return `${(value * 100).toFixed(fractionDigits)}%`;
}

export function formatSimulationNumber(
  value: number | null,
  fractionDigits = 2
): string {
  return value === null ? 'N/A' : value.toFixed(fractionDigits);
}

export function formatSimulationTimestamp(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

export function savedAnalysisTrajectory(
  analysis: PortfolioAnalysisResponse
): HistoricalScenarioTrajectoryPoint[] {
  let normalizedValue = 1;
  return [
    { date: analysis.start_date, normalized_value: normalizedValue },
    ...analysis.portfolio_returns.map((point) => {
      normalizedValue *= 1 + point.portfolio_return;
      return { date: point.date, normalized_value: normalizedValue };
    })
  ];
}

export function simulationTypeLabel(value: string): string {
  if (value === 'historical-scenario') return 'Historical Scenario';
  if (value === 'allocation') return 'Allocation Change';
  if (value === 'combined') return 'Combined Simulation';
  return value;
}
