import type { OutlookResponse, PortfolioMonetaryProjection } from '../../types/forecasting';

// Decimal strings stay exact for display. BigInt is used only to round/format
// backend amounts, never to derive a holding value or forecast in this client.
function decimalParts(value: unknown): { coefficient: bigint; scale: number } | null {
  if (typeof value !== 'string' || value.length > 1000) return null;
  const match = /^([+-]?)(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?$/.exec(value);
  if (!match) return null;
  const exponent = Number(match[4] ?? 0);
  if (!Number.isSafeInteger(exponent) || Math.abs(exponent) > 400) return null;
  return { coefficient: BigInt(`${match[1] === '-' ? '-' : ''}${match[2]}${match[3] ?? ''}`),
    scale: (match[3]?.length ?? 0) - exponent };
}

export function forecastMoney(value: string, currency: 'USD' | 'THB', signed = false): string {
  const parts = decimalParts(value);
  if (!parts) return 'N/A';
  const negative = parts.coefficient < 0n;
  const magnitude = negative ? -parts.coefficient : parts.coefficient;
  const shift = parts.scale - 2;
  const divisor = shift > 0 ? 10n ** BigInt(shift) : 1n;
  const cents = shift > 0 ? (magnitude + divisor / 2n) / divisor : magnitude * 10n ** BigInt(-shift);
  const sign = cents === 0n ? '' : negative ? '-' : signed ? '+' : '';
  return `${sign}${currency === 'THB' ? '฿' : '$'}${(cents / 100n).toLocaleString('en-US')}.${(cents % 100n).toString().padStart(2, '0')}`;
}

export const negativeMoney = (value: string) => (decimalParts(value)?.coefficient ?? 0n) < 0n;
const validDate = (value: unknown): value is string => typeof value === 'string'
  && /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(value))
  && new Date(value).toISOString().slice(0, 10) === value;

function validProjection(value: unknown, kind: 'current' | 'planned'): value is PortfolioMonetaryProjection {
  if (!value || typeof value !== 'object') return false;
  const money = value as PortfolioMonetaryProjection;
  const amount = decimalParts(money.baseline_amount);
  if (!amount || amount.coefficient <= 0n || !decimalParts(money.expected_change_amount)
      || !decimalParts(money.estimated_ending_value) || !['USD', 'THB'].includes(money.currency)
      || money.assumes_unchanged_fx !== (money.currency === 'THB')
      || !Array.isArray(money.limitations) || !money.limitations.length
      || !money.limitations.every(item => typeof item === 'string')) return false;
  if (kind === 'planned') return money.baseline_source === 'planned_investment' && money.hypothetical === true
    && money.valuation_requested_date === null && money.oldest_price_as_of === null && money.newest_price_as_of === null;
  return money.baseline_source === 'current_market_value' && money.hypothetical === false && money.currency === 'USD'
    && validDate(money.valuation_requested_date) && validDate(money.oldest_price_as_of) && validDate(money.newest_price_as_of)
    && money.oldest_price_as_of <= money.newest_price_as_of && money.newest_price_as_of <= money.valuation_requested_date;
}

export function validPortfolioMoney(result: OutlookResponse): boolean {
  if ('symbol' in result) return false;
  if (result.baseline_kind === 'legacy') return result.monetary_projection === null
    && result.components.every(item => item.monetary_projection === null);
  const parent = result.monetary_projection;
  if (!validProjection(parent, result.baseline_kind)) return false;
  return result.components.every(item => {
    const money = item.monetary_projection;
    return validProjection(money, result.baseline_kind as 'current' | 'planned') && money.currency === parent.currency
      && money.valuation_requested_date === parent.valuation_requested_date
      && money.oldest_price_as_of === money.newest_price_as_of
      && (result.baseline_kind === 'planned' || (money.oldest_price_as_of! >= parent.oldest_price_as_of!
        && money.newest_price_as_of! <= parent.newest_price_as_of!));
  });
}

export function monetaryContextKey(result: OutlookResponse): string | undefined {
  if ('symbol' in result || !result.monetary_projection) return undefined;
  const money = result.monetary_projection;
  return JSON.stringify([money.currency, money.baseline_source, money.baseline_amount, money.valuation_requested_date,
    money.oldest_price_as_of, money.newest_price_as_of,
    result.components.map(item => [item.symbol, item.monetary_projection?.baseline_amount]).sort((a, b) => a[0]!.localeCompare(b[0]!))]);
}
