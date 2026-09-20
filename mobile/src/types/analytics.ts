import type { IsoDate } from './api';

export type AnalysisPeriod = {
  start_date: IsoDate;
  end_date: IsoDate;
};

export type MaximumDrawdownMetrics = {
  max_drawdown: number;
  peak_date: IsoDate | null;
  trough_date: IsoDate | null;
};

export type ConcentrationMetrics = {
  largest_weight: number;
  top_n_weight: number;
  hhi: number;
  effective_number_of_assets: number;
  top_n: number;
};

export type DiversificationLevel =
  | 'Weak'
  | 'Moderate'
  | 'Strong'
  | 'Unavailable';

export type DiversificationMetrics = {
  active_asset_count: number;
  effective_number_of_assets: number;
  weight_score: number;
  average_pairwise_correlation: number | null;
  correlation_score: number | null;
  overall_score: number | null;
  level: DiversificationLevel;
  defined_pair_count: number;
  total_pair_count: number;
};

export type RiskMetricName =
  | 'volatility'
  | 'maximum_drawdown'
  | 'concentration'
  | 'diversification';

export type RiskLevel = 'Low' | 'Moderate' | 'High' | 'Very High';

export type RiskClassification = {
  risk_score: number;
  risk_level: RiskLevel;
  volatility_points: number;
  drawdown_points: number;
  concentration_points: number;
  diversification_points: number | null;
  metrics_used: RiskMetricName[];
  reasons: string[];
};

export type RiskDriverEntry = {
  rank: number;
  symbol: string;
  weight: number;
  annualized_asset_volatility: number;
  marginal_volatility_contribution: number;
  component_volatility_contribution: number;
  percentage_volatility_contribution: number;
};

export type RiskDriverAnalysis = {
  portfolio_volatility: number;
  top_driver: string;
  entries: RiskDriverEntry[];
};

export type AssetMetrics = {
  symbol: string;
  weight: number;
  cumulative_return: number;
  annualized_return: number;
  annualized_volatility: number;
  max_drawdown: number;
  sharpe_ratio: number | null;
  risk_classification?: AssetRiskClassification | null;
};

export type AssetRiskClassification = {
  risk_score: number;
  risk_level: RiskLevel;
  volatility_points: number;
  drawdown_points: number;
  metrics_used: Array<'volatility' | 'maximum_drawdown'>;
  reasons: string[];
};

export type CorrelationMatrixResponse = {
  symbols: string[];
  values: Array<Array<number | null>>;
};

export type CorrelationPair = {
  asset_a: string;
  asset_b: string;
  correlation: number | null;
};

export type AnalysisMetadata = {
  analysis_start: IsoDate;
  analysis_end: IsoDate;
  price_observation_count: number;
  return_observation_count: number;
  asset_count: number;
};

export type PortfolioMetrics = {
  cumulative_return: number;
  annualized_return: number;
  annualized_volatility: number;
  sharpe_ratio: number;
};

export type PortfolioReturnPoint = {
  date: IsoDate;
  portfolio_return: number;
};

export type AssetReturnPoint = {
  date: IsoDate;
  asset_return: number;
};

export type AssetReturnSeries = {
  symbol: string;
  points: AssetReturnPoint[];
};

export type PortfolioAnalysisResponse = AnalysisPeriod & {
  portfolio_name: string;
  metadata: AnalysisMetadata;
  portfolio_metrics: PortfolioMetrics;
  max_drawdown: MaximumDrawdownMetrics;
  concentration: ConcentrationMetrics;
  diversification: DiversificationMetrics;
  risk_classification: RiskClassification;
  risk_drivers: RiskDriverAnalysis;
  asset_metrics: AssetMetrics[];
  correlation_matrix: CorrelationMatrixResponse;
  correlation_pairs: CorrelationPair[];
  portfolio_returns: PortfolioReturnPoint[];
  asset_returns?: AssetReturnSeries[];
};
