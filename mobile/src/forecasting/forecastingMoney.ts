import type { OutlookResponse, PortfolioMonetaryProjection } from '../types/forecasting';

// String-only display rounding keeps backend Decimal cents intact on native
// runtimes. This does not calculate holdings, allocation or forecast amounts.
function decimalParts(value: unknown): { digits: string; negative: boolean; scale: number } | null {
  if (typeof value !== 'string' || value.length > 1000) return null;
  const match = /^([+-]?)(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?$/.exec(value);
  if (!match) return null;
  const exponent = Number(match[4] ?? 0);
  if (!Number.isSafeInteger(exponent) || Math.abs(exponent) > 400) return null;
  return { digits: `${match[2]}${match[3] ?? ''}`.replace(/^0+/, '') || '0',
    negative: match[1] === '-', scale: (match[3]?.length ?? 0) - exponent };
}

function increment(digits: string): string {
  const output = digits.split('');
  for (let index = output.length - 1; index >= 0; index--) {
    if (output[index] !== '9') { output[index] = String(Number(output[index]) + 1); return output.join(''); }
    output[index] = '0';
  }
  return `1${output.join('')}`;
}

export function forecastMoney(value: string, currency: 'USD' | 'THB', signed = false): string {
  const parts = decimalParts(value);
  if (!parts) return 'N/A';
  const shift = parts.scale - 2;
  const digits = shift > 0 ? parts.digits.padStart(shift + 1, '0') : parts.digits;
  let cents = shift > 0 ? digits.slice(0, -shift) : digits + '0'.repeat(-shift);
  if (shift > 0 && digits[digits.length - shift] >= '5') cents = increment(cents);
  cents = cents.replace(/^0+/, '') || '0';
  const padded = cents.padStart(3, '0');
  const sign = cents === '0' ? '' : parts.negative ? '-' : signed ? '+' : '';
  return `${sign}${currency === 'THB' ? '฿' : '$'}${padded.slice(0, -2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}.${padded.slice(-2)}`;
}

export const negativeMoney = (value: string) => {
  const parts = decimalParts(value);
  return Boolean(parts?.negative && parts.digits !== '0');
};
export const compactForecastMoney = (value: number, currency: 'USD' | 'THB', signed = false) => Math.abs(value) >= 1000
  ? new Intl.NumberFormat('en-US', { style: 'currency', currency, currencyDisplay: 'narrowSymbol',
    notation: 'compact', minimumFractionDigits: 0, maximumFractionDigits: 1, signDisplay: signed ? 'exceptZero' : 'auto' }).format(value)
  : forecastMoney(String(value), currency, signed);

const validDate = (value: unknown): value is string => typeof value === 'string'
  && /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(value))
  && new Date(value).toISOString().slice(0, 10) === value;

function validProjection(value: unknown, kind: 'current' | 'planned'): value is PortfolioMonetaryProjection {
  if (!value || typeof value !== 'object') return false;
  const money = value as PortfolioMonetaryProjection;
  const baseline = decimalParts(money.baseline_amount);
  if (!baseline || baseline.negative || baseline.digits === '0' || !decimalParts(money.expected_change_amount)
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
