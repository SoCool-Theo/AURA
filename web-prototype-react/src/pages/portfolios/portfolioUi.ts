import { ApiError } from '../../api/apiClient';
import type {
  DecimalString,
  PortfolioCurrency,
  PortfolioPlannedAllocationResponse,
  PortfolioPlannedPreviewResponse,
  PortfolioResponse,
  PortfolioType,
  PortfolioValuationResponse,
} from '../../types/portfolio';

export type PortfolioAllocationDisplayHolding = {
  symbol: string;
  weight: number;
};

export function portfolioErrorMessage(
  error: unknown,
  fallback: string,
): string {
  return error instanceof ApiError ? error.message : fallback;
}

export function formatPortfolioDate(value: string): string {
  return new Date(value).toLocaleString();
}

export function portfolioTypeLabel(type: PortfolioType): string {
  if (type === 'PLANNED') return 'Planned portfolio';
  if (type === 'LEGACY') return 'Legacy allocation';
  return 'Current portfolio';
}

function finiteDecimal(value: DecimalString): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function formatPortfolioMoney(
  value: DecimalString,
  currency: PortfolioCurrency,
): string {
  const parsed = finiteDecimal(value);
  if (parsed === null) return 'N/A';
  const symbol = currency === 'THB' ? '฿' : '$';
  return `${symbol}${parsed.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function formatSignedPortfolioMoney(
  value: DecimalString,
  currency: PortfolioCurrency,
): string {
  const parsed = finiteDecimal(value);
  if (parsed === null) return 'N/A';
  const symbol = currency === 'THB' ? '฿' : '$';
  const magnitude = Math.abs(parsed).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  if (parsed > 0) return `+${symbol}${magnitude}`;
  if (parsed < 0) return `−${symbol}${magnitude}`;
  return `${symbol}${magnitude}`;
}

export function formatPortfolioQuantity(value: DecimalString): string {
  const parsed = finiteDecimal(value);
  return parsed === null
    ? value
    : parsed.toLocaleString(undefined, { maximumFractionDigits: 12 });
}

export function formatPortfolioAllocation(value: DecimalString | number): string {
  const parsed = typeof value === 'number' ? value : finiteDecimal(value);
  return parsed === null || !Number.isFinite(parsed)
    ? 'N/A'
    : `${(parsed * 100).toFixed(2)}%`;
}

export function resolvedPortfolioAllocation(
  portfolio: PortfolioResponse,
  valuation: PortfolioValuationResponse | null,
  planned: PortfolioPlannedAllocationResponse | PortfolioPlannedPreviewResponse | null,
): PortfolioAllocationDisplayHolding[] {
  if (portfolio.portfolio_type === 'CURRENT') {
    return (valuation?.holdings ?? []).flatMap(holding => {
      const weight = finiteDecimal(holding.current_allocation);
      return weight === null ? [] : [{ symbol: holding.symbol, weight }];
    });
  }
  if (portfolio.portfolio_type === 'PLANNED') {
    return (planned?.holdings ?? []).flatMap(holding => {
      const weight = finiteDecimal(holding.target_allocation);
      return weight === null ? [] : [{ symbol: holding.symbol, weight }];
    });
  }
  return portfolio.holdings.flatMap(holding => (
    holding.weight == null
      ? []
      : [{ symbol: holding.symbol, weight: holding.weight }]
  ));
}
