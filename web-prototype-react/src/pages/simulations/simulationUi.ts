import { ApiError } from '../../api/apiClient';
import type {
  PortfolioHoldingInput,
  PortfolioPlannedAllocationResponse,
  PortfolioResponse,
  PortfolioValuationResponse,
} from '../../types/portfolio';
import type { SimulationHistoryDetailResponse, SimulationRunResult } from '../../types/simulation';

export type SimulationAllocationInputs = Record<string, string>;

const TOTAL_ALLOCATION_BASIS_POINTS = 10_000;

function allocationInputsFromRatios(
  entries: Array<{ symbol: string; ratio: number | null }>,
): SimulationAllocationInputs {
  const validEntries = entries.flatMap(({ symbol, ratio }, index) => (
    ratio !== null && Number.isFinite(ratio) && ratio >= 0
      ? [{ symbol, index, exactBasisPoints: ratio * TOTAL_ALLOCATION_BASIS_POINTS }]
      : []
  ));
  const targetBasisPoints = Math.round(validEntries.reduce(
    (total, entry) => total + entry.exactBasisPoints,
    0,
  ));
  const rounded = validEntries.map(entry => ({
    ...entry,
    basisPoints: Math.floor(entry.exactBasisPoints),
    remainder: entry.exactBasisPoints - Math.floor(entry.exactBasisPoints),
  }));
  let undistributed = targetBasisPoints - rounded.reduce(
    (total, entry) => total + entry.basisPoints,
    0,
  );
  for (const entry of [...rounded].sort((left, right) => (
    right.remainder - left.remainder || left.index - right.index
  ))) {
    if (undistributed <= 0) break;
    entry.basisPoints += 1;
    undistributed -= 1;
  }
  const bySymbol = new Map(rounded.map(entry => [entry.symbol, entry.basisPoints]));
  return Object.fromEntries(entries.map(({ symbol }) => [
    symbol,
    bySymbol.has(symbol) ? (bySymbol.get(symbol)! / 100).toFixed(2) : '',
  ]));
}

export function isAllocationPercentInput(value: string): boolean {
  return /^\d{0,3}(?:\.\d{0,2})?$/.test(value);
}

function parsedBasisPoints(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed || !isAllocationPercentInput(trimmed)) return null;
  const percent = Number(trimmed);
  if (!Number.isFinite(percent) || percent < 0 || percent > 100) return null;
  return Math.round(percent * 100);
}

export function rebalanceAllocationInputs(
  inputs: SimulationAllocationInputs,
  selectedSymbols: readonly string[],
  changedSymbol: string,
  value: string,
): SimulationAllocationInputs {
  const next = { ...inputs, [changedSymbol]: value };
  const changedBasisPoints = parsedBasisPoints(value);
  if (
    changedBasisPoints === null
    || selectedSymbols.length !== 2
    || !selectedSymbols.includes(changedSymbol)
  ) {
    return next;
  }

  const pairedSymbol = selectedSymbols.find(symbol => symbol !== changedSymbol)!;
  const unselectedSymbols = Object.keys(inputs).filter(
    symbol => !selectedSymbols.includes(symbol),
  );
  let unselectedTotalBasisPoints = 0;
  for (const symbol of unselectedSymbols) {
    const basisPoints = parsedBasisPoints(inputs[symbol] ?? '');
    if (basisPoints === null) return next;
    unselectedTotalBasisPoints += basisPoints;
  }
  const pairBasisPoints = (
    TOTAL_ALLOCATION_BASIS_POINTS - unselectedTotalBasisPoints
  );
  if (pairBasisPoints < 0) {
    return next;
  }
  const finalChangedBasisPoints = Math.min(changedBasisPoints, pairBasisPoints);
  if (finalChangedBasisPoints !== changedBasisPoints) {
    next[changedSymbol] = (finalChangedBasisPoints / 100).toFixed(2);
  }
  next[pairedSymbol] = (
    (pairBasisPoints - finalChangedBasisPoints) / 100
  ).toFixed(2);
  return next;
}

export function allocationInputsFromPortfolio(
  portfolio: PortfolioResponse,
): SimulationAllocationInputs {
  return allocationInputsFromRatios(portfolio.holdings.map(holding => ({
    symbol: holding.symbol,
    ratio: holding.weight,
  })));
}

export function allocationInputsFromValuation(
  valuation: PortfolioValuationResponse,
): SimulationAllocationInputs {
  return allocationInputsFromRatios(valuation.holdings.map(holding => {
    const weight = Number(holding.current_allocation);
    return { symbol: holding.symbol, ratio: Number.isFinite(weight) ? weight : null };
  }));
}

export function allocationInputsFromPlannedAllocation(
  allocation: PortfolioPlannedAllocationResponse,
): SimulationAllocationInputs {
  return allocationInputsFromRatios(allocation.holdings.map(holding => {
    const weight = Number(holding.target_allocation);
    return { symbol: holding.symbol, ratio: Number.isFinite(weight) ? weight : null };
  }));
}

export function validateModifiedAllocation(
  portfolio: PortfolioResponse,
  inputs: SimulationAllocationInputs,
): { allocation: PortfolioHoldingInput[]; error: null } | { allocation: null; error: string } {
  if (!portfolio.holdings.length) {
    return { allocation: null, error: 'This portfolio has no saved assets.' };
  }

  const savedSymbols = portfolio.holdings.map(holding => holding.symbol);
  const inputSymbols = Object.keys(inputs);
  if (
    inputSymbols.length !== savedSymbols.length
    || inputSymbols.some(symbol => !savedSymbols.includes(symbol))
  ) {
    return {
      allocation: null,
      error: 'The modified allocation must contain every saved asset.',
    };
  }

  const allocation: PortfolioHoldingInput[] = [];
  let totalPercent = 0;
  for (const holding of portfolio.holdings) {
    const rawValue = inputs[holding.symbol]?.trim() ?? '';
    const percent = Number(rawValue);
    if (
      !rawValue
      || !isAllocationPercentInput(rawValue)
      || !Number.isFinite(percent)
      || percent < 0
      || percent > 100
    ) {
      return {
        allocation: null,
        error: `${holding.symbol} needs an allocation from 0% through 100%.`,
      };
    }
    totalPercent += percent;
    allocation.push({ symbol: holding.symbol, weight: percent / 100 });
  }

  if (Math.abs(totalPercent - 100) > 1e-7) {
    return {
      allocation: null,
      error: `Total allocation must equal 100%. Current total: ${totalPercent.toFixed(2)}%.`,
    };
  }
  return { allocation, error: null };
}

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

export function simulationTypeLabel(value: string): string {
  if (value === 'historical-scenario') return 'Historical Scenario';
  if (value === 'allocation') return 'Allocation Change';
  if (value === 'combined') return 'Combined Simulation';
  return value;
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
