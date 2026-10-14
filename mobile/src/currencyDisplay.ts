import type { OutlookResponse } from './types/forecasting';
import type { PlannedPortfolioBaselineContext } from './types/portfolio';
import type { SimulationBaselineValuationContext } from './types/simulation';

export type DisplayCurrency = 'USD' | 'THB';
export type CurrencyDisplayHolding = {
  symbol: string; baseline_amount: string;
  expected_change_amount: string | null; estimated_ending_value: string | null;
};
export type CurrencyDisplayView = {
  currency: DisplayCurrency; baseline_amount: string;
  expected_change_amount: string | null; estimated_ending_value: string | null;
  holdings: CurrencyDisplayHolding[];
};
export type CurrencyDisplayContext = {
  baseline_kind: 'current' | 'planned'; source_currency: DisplayCurrency; requested_date: string | null;
  fx: { pair: 'USD/THB'; provider_symbol: 'THB=X'; rate: string; as_of: string } | null;
  views: CurrencyDisplayView[];
};

export function validCurrencyDisplay(display: CurrencyDisplayContext): boolean {
  const amount = (value: unknown) => typeof value === 'string' && /^[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$/.test(value);
  const positive = (value: unknown) => amount(value) && !String(value).startsWith('-') && /[1-9]/.test(String(value).split(/[eE]/)[0]);
  const date = (value: unknown): value is string => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value))
    && new Date(value).toISOString().slice(0, 10) === value;
  if (!display || !['current', 'planned'].includes(display.baseline_kind) || !date(display.requested_date)
    || !Array.isArray(display.views) || display.views.length < 1 || display.views.length > 2) return false;
  const currencies = display.views.map(view => view.currency);
  if (currencies[0] !== display.source_currency || new Set(currencies).size !== currencies.length
    || currencies.some(currency => currency !== 'USD' && currency !== 'THB')) return false;
  if (display.fx) {
    const age = (Date.parse(display.requested_date) - Date.parse(display.fx.as_of)) / 86400000;
    if (display.fx.pair !== 'USD/THB' || display.fx.provider_symbol !== 'THB=X' || !positive(display.fx.rate)
      || !date(display.fx.as_of) || age < 0 || age > 4) return false;
  } else if (currencies.length > 1) return false;
  if (!Array.isArray(display.views[0].holdings)) return false;
  const symbols = display.views[0].holdings.map(holding => holding.symbol);
  if (!symbols?.length || new Set(symbols).size !== symbols.length) return false;
  return display.views.every(view => {
    const projected = view.expected_change_amount !== null;
    return positive(view.baseline_amount) && (projected ? amount(view.expected_change_amount) && amount(view.estimated_ending_value) : view.estimated_ending_value === null)
      && Array.isArray(view.holdings) && view.holdings.length === symbols.length && view.holdings.every((holding, index) =>
        holding.symbol === symbols[index] && positive(holding.baseline_amount)
        && (projected ? amount(holding.expected_change_amount) && amount(holding.estimated_ending_value)
          : holding.expected_change_amount === null && holding.estimated_ending_value === null));
  });
}

export function validForecastCurrencyDisplay(result: OutlookResponse): boolean {
  if ('symbol' in result || !result.currency_display) return true;
  const display = result.currency_display, source = display.views?.[0], money = result.monetary_projection;
  if (!validCurrencyDisplay(display) || !money || display.baseline_kind !== result.baseline_kind
    || display.source_currency !== money.currency || source.baseline_amount !== money.baseline_amount
    || source.expected_change_amount !== money.expected_change_amount || source.estimated_ending_value !== money.estimated_ending_value) return false;
  return source.holdings.length === result.components.length && result.components.every(component => {
    const holding = source.holdings.find(item => item.symbol === component.symbol), projection = component.monetary_projection;
    return holding && projection && holding.baseline_amount === projection.baseline_amount
      && holding.expected_change_amount === projection.expected_change_amount && holding.estimated_ending_value === projection.estimated_ending_value;
  });
}

// Presentation-only copies use complete backend views, never client FX arithmetic.
export function outlookCurrencyView(result: OutlookResponse, currency?: DisplayCurrency): OutlookResponse {
  if ('symbol' in result || !result.currency_display || !validForecastCurrencyDisplay(result)) return result;
  const view = result.currency_display.views.find(item => item.currency === currency);
  if (!view || !result.monetary_projection) return result;
  const money = (projection: NonNullable<typeof result.monetary_projection>, amounts: CurrencyDisplayHolding | CurrencyDisplayView) => ({
    ...projection, currency: view.currency, baseline_amount: amounts.baseline_amount,
    expected_change_amount: amounts.expected_change_amount!, estimated_ending_value: amounts.estimated_ending_value!,
    assumes_unchanged_fx: view.currency === 'THB',
  });
  return { ...result, monetary_projection: money(result.monetary_projection, view), components: result.components.map(component => ({
    ...component, monetary_projection: money(component.monetary_projection!, view.holdings.find(holding => holding.symbol === component.symbol)!),
  })) } as OutlookResponse;
}

export function forecastDisplayContext(results: OutlookResponse[] = []): CurrencyDisplayContext | null {
  const portfolios = results.filter(result => 'portfolio_id' in result);
  const display = portfolios.find(result => result.currency_display)?.currency_display;
  if (!display || !validCurrencyDisplay(display)) return null;
  const views = display.views.filter(view => portfolios.every(result =>
    result.currency_display?.views.some(item => item.currency === view.currency)
      ?? result.monetary_projection?.currency === view.currency));
  return views.length ? { ...display, views } : null;
}

export function simulationCurrencyDisplay(display?: CurrencyDisplayContext | null,
  baseline?: SimulationBaselineValuationContext | PlannedPortfolioBaselineContext): CurrencyDisplayContext | null {
  if (display && validCurrencyDisplay(display)) return display;
  if (!baseline) return null;
  const planned = 'portfolio_type' in baseline;
  return { baseline_kind: planned ? 'planned' : 'current', source_currency: planned ? baseline.plan_currency : 'USD',
    requested_date: planned ? null : baseline.valuation_date, fx: null,
    views: [{ currency: planned ? baseline.plan_currency : 'USD', baseline_amount: planned ? baseline.total_proposed_amount : baseline.total_current_value_usd,
      expected_change_amount: null, estimated_ending_value: null,
      holdings: baseline.holdings.map(holding => ({ symbol: holding.symbol,
        baseline_amount: 'proposed_amount' in holding ? holding.proposed_amount : holding.current_value_usd,
        expected_change_amount: null, estimated_ending_value: null,
      })),
    }],
  };
}
