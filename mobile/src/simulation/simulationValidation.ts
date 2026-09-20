import type { PortfolioResponse } from '../types/portfolio';
import type {
  PortfolioAllocationInput,
  PortfolioPlannedAllocationResponse,
  PortfolioValuationResponse
} from '../types/portfolio';

export type AllocationInputs = Record<string, string>;

export type AllocationValidationResult =
  | { allocation: PortfolioAllocationInput[]; error: null }
  | { allocation: null; error: string };

export function allocationInputsFromPortfolio(
  portfolio: PortfolioResponse
): AllocationInputs {
  return Object.fromEntries(portfolio.holdings.map((holding) => [
    holding.symbol,
    holding.weight === null
      ? ''
      : String(Number((holding.weight * 100).toFixed(10)))
  ]));
}

export function allocationInputsFromValuation(
  valuation: PortfolioValuationResponse
): AllocationInputs {
  return Object.fromEntries(valuation.holdings.map((holding) => {
    const allocation = Number(holding.current_allocation);
    return [
      holding.symbol,
      Number.isFinite(allocation)
        ? String(Number((allocation * 100).toFixed(10)))
        : ''
    ];
  }));
}

export function allocationInputsFromPlannedAllocation(
  allocation: PortfolioPlannedAllocationResponse
): AllocationInputs {
  return Object.fromEntries(allocation.holdings.map((holding) => {
    const target = Number(holding.target_allocation);
    return [
      holding.symbol,
      Number.isFinite(target)
        ? String(Number((target * 100).toFixed(10)))
        : ''
    ];
  }));
}

export function validateModifiedAllocation(
  portfolio: PortfolioResponse,
  inputs: AllocationInputs
): AllocationValidationResult {
  if (!portfolio.holdings.length) {
    return { allocation: null, error: 'This portfolio has no saved holdings.' };
  }

  const savedSymbols = portfolio.holdings.map((holding) => holding.symbol);
  const inputSymbols = Object.keys(inputs);
  if (
    inputSymbols.length !== savedSymbols.length
    || inputSymbols.some((symbol) => !savedSymbols.includes(symbol))
  ) {
    return {
      allocation: null,
      error: 'The modified allocation must contain the complete saved symbol set.'
    };
  }

  const allocation: PortfolioAllocationInput[] = [];
  let totalPercent = 0;
  for (const holding of portfolio.holdings) {
    const rawValue = inputs[holding.symbol]?.trim() ?? '';
    const percent = Number(rawValue);
    if (
      !rawValue
      || !Number.isFinite(percent)
      || percent < 0
      || percent > 100
    ) {
      return {
        allocation: null,
        error: `${holding.symbol} needs a weight from 0% through 100%.`
      };
    }
    totalPercent += percent;
    allocation.push({ symbol: holding.symbol, weight: percent / 100 });
  }

  if (Math.abs(totalPercent - 100) > 1e-7) {
    return {
      allocation: null,
      error: `Total allocation must equal 100%. Current total: ${totalPercent.toFixed(2)}%.`
    };
  }

  return { allocation, error: null };
}

export function allocationTotal(inputs: AllocationInputs): number {
  return Object.values(inputs).reduce((total, value) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? total + parsed : total;
  }, 0);
}

export function isValidIsoDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split('-').map(Number);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return parsed.getUTCFullYear() === year
    && parsed.getUTCMonth() === month - 1
    && parsed.getUTCDate() === day;
}

function localIsoDate(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

export function defaultSimulationPeriod(): { start: string; end: string } {
  const end = new Date();
  const start = new Date(end);
  start.setFullYear(start.getFullYear() - 1);
  return { start: localIsoDate(start), end: localIsoDate(end) };
}
