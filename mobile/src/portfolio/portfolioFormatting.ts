import type { DecimalString, PortfolioCurrency } from '../types/portfolio';

function finiteDecimal(value: DecimalString): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function formatPortfolioMoney(
  value: DecimalString,
  currency: PortfolioCurrency
): string {
  const parsed = finiteDecimal(value);
  if (parsed === null) return 'N/A';
  const symbol = currency === 'THB' ? '฿' : '$';
  return `${symbol}${parsed.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })}`;
}

export function formatPortfolioQuantity(value: DecimalString): string {
  const parsed = finiteDecimal(value);
  if (parsed === null) return value;
  return parsed.toLocaleString(undefined, { maximumFractionDigits: 12 });
}

export function formatCurrentAllocation(value: DecimalString): string {
  const parsed = finiteDecimal(value);
  return parsed === null ? 'N/A' : `${(parsed * 100).toFixed(2)}%`;
}

export function currentAllocationPercent(value: DecimalString): number {
  const parsed = finiteDecimal(value);
  return parsed === null ? 0 : parsed * 100;
}
