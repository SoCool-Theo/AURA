import { ApiError } from '../../api/apiClient';
import type { OutlookResponse, ForecastPredictionInterval, AssetOutlookResponse } from '../../types/forecasting';

export const forecastHorizons = [7, 14, 21, 30] as const;
export type OutlookMetric = 'return' | 'volatility';
export type OutlookPoint = { horizonDays: number; estimate: number; interval?: ForecastPredictionInterval };
export const forecastPercent = (value: number, signed = false) => Number.isFinite(value)
  ? `${signed && value > 0 ? '+' : ''}${(value * 100).toFixed(2)}%` : 'N/A';
export const forecastBaselineLabel = (kind: 'current' | 'planned' | 'legacy') =>
  kind === 'planned' ? 'Planned target allocation · hypothetical' : kind === 'legacy' ? 'Legacy saved allocation' : 'Current allocation · USD valuation';

export function validOutlookResponse(result: OutlookResponse, scope: 'portfolio' | 'asset', selection: string): boolean {
  const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);
  const interval = (value: ForecastPredictionInterval) => value && value.coverage === 0.80 && finite(value.lower) && finite(value.upper) && value.lower <= value.upper;
  const common = (value: OutlookResponse) => value && value.horizon_days === 30 && finite(value.expected_return_30d)
    && finite(value.forecast_realized_volatility_30d) && value.forecast_realized_volatility_30d >= 0
    && typeof value.artifact_version === 'string' && typeof value.market_data_as_of === 'string'
    && Array.isArray(value.limitations) && value.limitations.every(item => typeof item === 'string');
  const asset = (value: AssetOutlookResponse) => common(value) && typeof value.symbol === 'string'
    && typeof value.forecast_origin_date === 'string' && typeof value.return_model_id === 'string'
    && typeof value.volatility_model_id === 'string' && finite(value.market_data_age_days)
    && interval(value.return_prediction_interval) && interval(value.volatility_prediction_interval)
    && value.volatility_prediction_interval.lower >= 0;
  if (!common(result)) return false;
  if (scope === 'asset') return 'symbol' in result && result.symbol === selection && asset(result);
  return 'portfolio_id' in result && result.portfolio_id === selection && typeof result.portfolio_name === 'string'
    && ['current', 'planned', 'legacy'].includes(result.baseline_kind)
    && typeof result.correlation_as_of_date === 'string' && finite(result.correlation_observation_count)
    && Array.isArray(result.components) && result.components.length > 0 && result.components.every(item => asset(item)
      && finite(item.current_weight) && item.current_weight >= 0 && item.current_weight <= 1
      && finite(item.forecast_volatility_contribution) && finite(item.forecast_volatility_contribution_share));
}
export function forecastPoints(result: OutlookResponse, metric: OutlookMetric): OutlookPoint[] {
  // One actual backend estimate. Never interpolate other horizons from V1.
  return [{
    horizonDays: result.horizon_days,
    estimate: metric === 'return' ? result.expected_return_30d : result.forecast_realized_volatility_30d,
    interval: 'symbol' in result ? metric === 'return' ? result.return_prediction_interval : result.volatility_prediction_interval : undefined,
  }];
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
