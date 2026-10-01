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

const TOTAL_ALLOCATION_BASIS_POINTS = 10_000;

function allocationInputsFromRatios(
  entries: Array<{ symbol: string; ratio: number | null }>
): AllocationInputs {
  const percentages = entries.map(({ symbol, ratio }) => ({
    symbol,
    value: ratio !== null && Number.isFinite(ratio) ? ratio * 100 : null
  }));
  const rounded = percentages.map(({ symbol, value }) => ({
    symbol,
    value: value === null ? null : Number(value.toFixed(2))
  }));
  let lastValidIndex = -1;
  for (let index = rounded.length - 1; index >= 0; index -= 1) {
    if (rounded[index].value !== null) {
      lastValidIndex = index;
      break;
    }
  }

  if (lastValidIndex >= 0) {
    const exactTotal = percentages.reduce(
      (total, { value }) => total + (value ?? 0),
      0
    );
    const roundedTotal = rounded.reduce(
      (total, { value }) => total + (value ?? 0),
      0
    );
    const correction = Number(
      (Number(exactTotal.toFixed(2)) - roundedTotal).toFixed(2)
    );
    const finalValue = rounded[lastValidIndex].value;
    if (finalValue !== null && correction !== 0) {
      rounded[lastValidIndex] = {
        ...rounded[lastValidIndex],
        value: Number((finalValue + correction).toFixed(2))
      };
    }
  }

  return Object.fromEntries(rounded.map(({ symbol, value }) => [
    symbol,
    value === null ? '' : value.toFixed(2)
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
  inputs: AllocationInputs,
  selectedSymbols: readonly string[],
  changedSymbol: string,
  value: string
): AllocationInputs {
  const next = { ...inputs, [changedSymbol]: value };
  const changedBasisPoints = parsedBasisPoints(value);
  if (
    changedBasisPoints === null
    || selectedSymbols.length !== 2
    || !selectedSymbols.includes(changedSymbol)
  ) {
    return next;
  }

  const pairedSymbol = selectedSymbols.find((symbol) => symbol !== changedSymbol)!;
  const unselectedSymbols = Object.keys(inputs).filter(
    (symbol) => !selectedSymbols.includes(symbol)
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
  portfolio: PortfolioResponse
): AllocationInputs {
  return allocationInputsFromRatios(portfolio.holdings.map((holding) => ({
    symbol: holding.symbol,
    ratio: holding.weight
  })));
}

export function allocationInputsFromValuation(
  valuation: PortfolioValuationResponse
): AllocationInputs {
  return allocationInputsFromRatios(valuation.holdings.map((holding) => ({
    symbol: holding.symbol,
    ratio: Number(holding.current_allocation)
  })));
}

export function allocationInputsFromPlannedAllocation(
  allocation: PortfolioPlannedAllocationResponse
): AllocationInputs {
  return allocationInputsFromRatios(allocation.holdings.map((holding) => ({
    symbol: holding.symbol,
    ratio: Number(holding.target_allocation)
  })));
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
      || !isAllocationPercentInput(rawValue)
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
