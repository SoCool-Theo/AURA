import { ApiError } from '../../api/apiClient';
import type { OutlookResponse, ForecastPredictionInterval, AnyAssetOutlookResponse, ForecastHorizon } from '../../types/forecasting';

export const forecastHorizons = [7, 14, 21, 30] as const;
export type OutlookMetric = 'return' | 'volatility';
export type OutlookPoint = { horizonDays: number; estimate: number; interval?: ForecastPredictionInterval; dataDate?: string; experimental?: boolean };
export const forecastReturn = (result: OutlookResponse) => result.horizon_days === 30 ? result.expected_return_30d : result.expected_return;
export const forecastVolatility = (result: OutlookResponse) => result.horizon_days === 30 ? result.forecast_realized_volatility_30d : result.forecast_realized_volatility;
export const forecastPercent = (value: number, signed = false) => Number.isFinite(value)
  ? `${signed && value > 0 ? '+' : ''}${(value * 100).toFixed(2)}%` : 'N/A';
export const forecastBaselineLabel = (kind: 'current' | 'planned' | 'legacy') =>
  kind === 'planned' ? 'Planned target allocation · hypothetical' : kind === 'legacy' ? 'Legacy saved allocation' : 'Current allocation · USD valuation';

export function validOutlookResponse(result: OutlookResponse, scope: 'portfolio' | 'asset', selection: string, horizon: ForecastHorizon = 30): boolean {
  const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);
  const interval = (value: ForecastPredictionInterval) => value && value.coverage === 0.80 && finite(value.lower) && finite(value.upper) && value.lower <= value.upper;
  const strings = (value: unknown) => Array.isArray(value) && value.every(item => typeof item === 'string');
  const common = (value: OutlookResponse) => value && value.horizon_days === horizon
    && forecastHorizons.includes(value.horizon_days) && finite(forecastReturn(value))
    && finite(forecastVolatility(value)) && forecastVolatility(value) >= 0
    && typeof value.artifact_version === 'string' && typeof value.market_data_as_of === 'string'
    && strings(value.limitations) && (value.horizon_days === 30 || (
      value.horizon_unit === 'calendar_days' && value.artifact_version === 'forecast-weekly-v1-20260917'
      && value.experimental === true && value.predictive_quality_approved === false
      && value.quality_status === 'experimental_educational_not_predictive_quality_approved'));
  const asset = (value: AnyAssetOutlookResponse) => common(value) && typeof value.symbol === 'string'
    && typeof value.forecast_origin_date === 'string' && typeof value.return_model_id === 'string'
    && typeof value.volatility_model_id === 'string' && finite(value.market_data_age_days)
    && interval(value.return_prediction_interval) && interval(value.volatility_prediction_interval)
    && value.volatility_prediction_interval.lower >= 0
    && (value.horizon_days === 30 || (strings(value.return_warning_codes) && strings(value.volatility_warning_codes)
      && Number.isInteger(value.market_data_age_days) && value.market_data_age_days >= 0 && value.market_data_age_days <= 4
      && value.market_data_as_of === value.forecast_origin_date));
  if (!common(result)) return false;
  if (scope === 'asset') return 'symbol' in result && result.symbol === selection && asset(result);
  return 'portfolio_id' in result && result.portfolio_id === selection && typeof result.portfolio_name === 'string'
    && ['current', 'planned', 'legacy'].includes(result.baseline_kind)
    && typeof result.correlation_as_of_date === 'string' && finite(result.correlation_observation_count)
    && Array.isArray(result.components) && result.components.length > 0 && result.components.every(item => asset(item)
      && item.artifact_version === result.artifact_version
      && finite(item.current_weight) && item.current_weight >= 0 && item.current_weight <= 1
      && finite(item.forecast_volatility_contribution) && finite(item.forecast_volatility_contribution_share));
}
export function forecastPoints(result: OutlookResponse, metric: OutlookMetric): OutlookPoint[] {
  // One actual backend estimate. Never scale or interpolate a different horizon.
  return [{
    horizonDays: result.horizon_days,
    estimate: metric === 'return' ? forecastReturn(result) : forecastVolatility(result),
    interval: 'symbol' in result ? metric === 'return' ? result.return_prediction_interval : result.volatility_prediction_interval : undefined,
  }];
}
export function comparisonPoints(results: OutlookResponse[], metric: OutlookMetric): OutlookPoint[] {
  return [...results].sort((a, b) => a.horizon_days - b.horizon_days).map(result => ({
    ...forecastPoints(result, metric)[0], dataDate: result.market_data_as_of, experimental: result.horizon_days !== 30,
  }));
}
export function forecastWarnings(results: OutlookResponse[]) {
  const messages: Record<string, string> = {
    arima_fit_convergence_warning: 'The selected ARIMA model reported a fit-convergence warning during offline evaluation.',
    empty_volatility_intervals_counted_as_misses: 'Empty volatility ranges occurred during evaluation and were counted as misses.',
    final_interval_coverage_below_nominal: 'Observed evaluation coverage was below the nominal 80% prediction range.',
  };
  return results.flatMap(result => ('symbol' in result ? [result] : result.components).flatMap(item =>
    item.horizon_days === 30 ? [] : (['return', 'volatility'] as const).flatMap(target =>
      item[target === 'return' ? 'return_warning_codes' : 'volatility_warning_codes'].map(code => ({
        key: `${item.horizon_days}:${item.symbol}:${target}:${code}`,
        label: `${item.horizon_days}-day ${item.symbol} ${target}`,
        message: Object.hasOwn(messages, code) ? messages[code] : 'The backend retained an additional model-quality warning.',
      })))));
}
export function forecastErrorMessage(error: unknown, scope: 'portfolio' | 'asset'): string {
  if (error instanceof ApiError) {
    if (error.status === 503) {
      if (error.detail === 'Forecast unavailable because current market data is stale.') return 'Saved market data is too old for this outlook. The backend updater must refresh it before you try again.';
      if (error.detail === 'Forecast unavailable because market history is insufficient.') return 'There is not enough saved market history to generate this outlook.';
      return 'This outlook is currently unavailable. Required market data or model artifacts may be unavailable. Try again later.';
    }
    if (error.status === 409) return 'This portfolio cannot provide an outlook in its current holding state. Review its holdings and allocation.';
    if (error.status === 404) return scope === 'asset' ? 'This asset is not supported for forecasting.' : 'This portfolio is unavailable or no longer belongs to your account.';
    if (error.status === 401) return 'Your session has expired. Sign in again to view this outlook.';
    if (error.kind === 'network') return 'Unable to reach Aura. Check your connection and try again.';
  }
  return 'Unable to load this outlook. Please try again.';
}
