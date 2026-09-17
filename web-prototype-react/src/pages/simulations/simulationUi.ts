import { ApiError } from '../../api/apiClient';
import type {
  PortfolioHoldingInput,
  PortfolioPlannedAllocationResponse,
  PortfolioResponse,
  PortfolioValuationResponse,
} from '../../types/portfolio';
import type { SimulationHistoryDetailResponse, SimulationRunResult } from '../../types/simulation';

export type SimulationAllocationInputs = Record<string, string>;

function percentInput(weight: number): string {
  return String(Number((weight * 100).toFixed(10)));
}

export function allocationInputsFromPortfolio(
  portfolio: PortfolioResponse,
): SimulationAllocationInputs {
  return Object.fromEntries(portfolio.holdings.map(holding => [
    holding.symbol,
    holding.weight == null ? '' : percentInput(holding.weight),
  ]));
}

export function allocationInputsFromValuation(
  valuation: PortfolioValuationResponse,
): SimulationAllocationInputs {
  return Object.fromEntries(valuation.holdings.map(holding => {
    const weight = Number(holding.current_allocation);
    return [holding.symbol, Number.isFinite(weight) ? percentInput(weight) : ''];
  }));
}

export function allocationInputsFromPlannedAllocation(
  allocation: PortfolioPlannedAllocationResponse,
): SimulationAllocationInputs {
  return Object.fromEntries(allocation.holdings.map(holding => {
    const weight = Number(holding.target_allocation);
    return [holding.symbol, Number.isFinite(weight) ? percentInput(weight) : ''];
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
    if (!rawValue || !Number.isFinite(percent) || percent < 0 || percent > 100) {
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
