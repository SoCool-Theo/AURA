export type ForecastPredictionInterval = { lower: number; upper: number; coverage: 0.80 };
export type AssetOutlookResponse = {
  symbol: string;
  forecast_origin_date: string;
  horizon_days: 30;
  expected_return_30d: number;
  return_prediction_interval: ForecastPredictionInterval;
  forecast_realized_volatility_30d: number;
  volatility_prediction_interval: ForecastPredictionInterval;
  market_data_as_of: string;
  market_data_age_days: number;
  artifact_version: string;
  return_model_id: string;
  volatility_model_id: string;
  limitations: string[];
};
export type PortfolioOutlookComponent = AssetOutlookResponse & {
  current_weight: number;
  forecast_volatility_contribution: number;
  forecast_volatility_contribution_share: number;
};
export type PortfolioOutlookResponse = {
  portfolio_id: string;
  portfolio_name: string;
  baseline_kind: 'current' | 'planned' | 'legacy';
  horizon_days: 30;
  expected_return_30d: number;
  forecast_realized_volatility_30d: number;
  correlation_as_of_date: string;
  correlation_observation_count: number;
  market_data_as_of: string;
  artifact_version: string;
  components: PortfolioOutlookComponent[];
  limitations: string[];
};
export type WeeklyHorizon = 7 | 14 | 21;
export type ForecastHorizon = WeeklyHorizon | 30;
type WeeklyQuality = {
  horizon_days: WeeklyHorizon;
  horizon_unit: 'calendar_days';
  expected_return: number;
  forecast_realized_volatility: number;
  artifact_version: 'forecast-weekly-v1-20260917';
  experimental: true;
  predictive_quality_approved: false;
  quality_status: 'experimental_educational_not_predictive_quality_approved';
};
export type WeeklyAssetOutlookResponse = Omit<AssetOutlookResponse,
  'horizon_days' | 'expected_return_30d' | 'forecast_realized_volatility_30d' | 'artifact_version'> & WeeklyQuality & {
  return_warning_codes: string[];
  volatility_warning_codes: string[];
};
export type WeeklyPortfolioOutlookComponent = WeeklyAssetOutlookResponse & Pick<PortfolioOutlookComponent,
  'current_weight' | 'forecast_volatility_contribution' | 'forecast_volatility_contribution_share'>;
export type WeeklyPortfolioOutlookResponse = Omit<PortfolioOutlookResponse,
  'horizon_days' | 'expected_return_30d' | 'forecast_realized_volatility_30d' | 'artifact_version' | 'components'> & WeeklyQuality & {
  components: WeeklyPortfolioOutlookComponent[];
};
export type AnyAssetOutlookResponse = AssetOutlookResponse | WeeklyAssetOutlookResponse;
export type OutlookResponse = AnyAssetOutlookResponse | PortfolioOutlookResponse | WeeklyPortfolioOutlookResponse;
