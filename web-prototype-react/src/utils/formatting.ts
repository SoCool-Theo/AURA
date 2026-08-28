const usdFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 2,
});

export function money(value: number): string {
  return usdFormatter.format(value);
}

export function pct(value: number, digits = 2): string {
  return `${value >= 0 ? '+' : ''}${Number(value).toFixed(digits)}%`;
}
