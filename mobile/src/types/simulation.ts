import type { AnalysisPeriod, MaximumDrawdownMetrics } from './analytics';
import type { IsoDate, IsoDateTime, Uuid } from './api';
import type {
  DecimalString,
  PlannedPortfolioBaselineContext,
  PortfolioAllocationInput,
  PortfolioCurrency
} from './portfolio';

export type HistoricalScenarioResponse = {
  id: string;
  display_name: string;
  description: string;
  requested_start_date: IsoDate;
  requested_end_date: IsoDate;
};

export type HistoricalScenarioListResponse = {
  scenarios: HistoricalScenarioResponse[];
};

export type HistoricalScenarioSimulationRequest = {
  scenario_id: string;
};

export type HistoricalScenarioSimulationMetadata = {
  effective_start_date: IsoDate;
  effective_end_date: IsoDate;
  price_observation_count: number;
  return_observation_count: number;
};

export type HistoricalScenarioTrajectoryPoint = {
  date: IsoDate;
  normalized_value: number;
};

export type HistoricalScenarioMetrics = {
  normalized_starting_value: number;
  normalized_ending_value: number;
  cumulative_return: number;
  annualized_volatility: number;
  sharpe_ratio: number | null;
  maximum_drawdown: MaximumDrawdownMetrics;
};

export type HistoricalScenarioSimulationResponse = {
  portfolio_id: Uuid;
  portfolio_name: string;
  scenario: HistoricalScenarioResponse;
  metadata: HistoricalScenarioSimulationMetadata;
  metrics: HistoricalScenarioMetrics;
  trajectory: HistoricalScenarioTrajectoryPoint[];
};

export type AllocationSimulationRequest = AnalysisPeriod & {
  modified_allocation: PortfolioAllocationInput[];
};

export type CombinedSimulationRequest = HistoricalScenarioSimulationRequest & {
  modified_allocation: PortfolioAllocationInput[];
};

export type AllocationSimulationResult = {
  allocation: PortfolioAllocationInput[];
  metrics: HistoricalScenarioMetrics;
  trajectory: HistoricalScenarioTrajectoryPoint[];
};

export type AllocationSimulationComparison = {
  normalized_ending_value_delta: number;
  cumulative_return_delta: number;
  annualized_volatility_delta: number;
  sharpe_ratio_delta: number | null;
  maximum_drawdown_delta: number;
};

export type AllocationSimulationResponse = AnalysisPeriod & {
  portfolio_id: Uuid;
  portfolio_name: string;
  metadata: HistoricalScenarioSimulationMetadata;
  original: AllocationSimulationResult;
  modified: AllocationSimulationResult;
  comparison: AllocationSimulationComparison;
};

export type CombinedSimulationResponse = {
  portfolio_id: Uuid;
  portfolio_name: string;
  scenario: HistoricalScenarioResponse;
  metadata: HistoricalScenarioSimulationMetadata;
  original: AllocationSimulationResult;
  modified: AllocationSimulationResult;
  comparison: AllocationSimulationComparison;
};

export type SimulationType = 'historical-scenario' | 'allocation' | 'combined';

type SimulationHistoryShared = {
  id: Uuid;
  portfolio_id: Uuid;
  requested_start_date: IsoDate;
  requested_end_date: IsoDate;
  created_at: IsoDateTime;
};

export type HistoricalScenarioHistorySummary = SimulationHistoryShared & {
  simulation_type: 'historical-scenario';
  scenario_id: string;
};

export type AllocationHistorySummary = SimulationHistoryShared & {
  simulation_type: 'allocation';
  scenario_id: null;
};

export type CombinedHistorySummary = SimulationHistoryShared & {
  simulation_type: 'combined';
  scenario_id: string;
};

export type SimulationHistorySummary =
  | HistoricalScenarioHistorySummary
  | AllocationHistorySummary
  | CombinedHistorySummary;

export type SimulationHistoryListResponse = {
  simulations: SimulationHistorySummary[];
};

export type SimulationHistoryV1DetailResponse =
  | (HistoricalScenarioHistorySummary & {
    result: HistoricalScenarioSimulationResponse;
  })
  | (AllocationHistorySummary & {
    result: AllocationSimulationResponse;
  })
  | (CombinedHistorySummary & {
    result: CombinedSimulationResponse;
  });

export type SimulationBaselineHolding = {
  id: Uuid | null;
  symbol: string;
  invested_amount: DecimalString | null;
  invested_currency: PortfolioCurrency | null;
  shares: DecimalString;
  purchase_date: IsoDate | null;
  position: number;
  asset_price: DecimalString;
  asset_quote_currency: 'USD';
  price_as_of: IsoDate;
  current_value_usd: DecimalString;
  current_allocation: DecimalString;
};

export type SimulationBaselineValuationContext = {
  valuation_currency: 'USD';
  valuation_date: IsoDate;
  oldest_price_as_of: IsoDate;
  newest_price_as_of: IsoDate;
  total_current_value_usd: DecimalString;
  holdings: SimulationBaselineHolding[];
};

export type HistoricalScenarioHistoryV2Detail =
  HistoricalScenarioHistorySummary & {
    schema_version: 'historical-scenario-simulation-response-v2';
    baseline: SimulationBaselineValuationContext;
    result: HistoricalScenarioSimulationResponse;
  };

export type AllocationHistoryV2Detail = AllocationHistorySummary & {
  schema_version: 'allocation-simulation-response-v2';
  baseline: SimulationBaselineValuationContext;
  result: AllocationSimulationResponse;
};

export type CombinedHistoryV2Detail = CombinedHistorySummary & {
  schema_version: 'combined-simulation-response-v2';
  baseline: SimulationBaselineValuationContext;
  result: CombinedSimulationResponse;
};

export type SimulationHistoryV2DetailResponse =
  | HistoricalScenarioHistoryV2Detail
  | AllocationHistoryV2Detail
  | CombinedHistoryV2Detail;

export type HistoricalScenarioHistoryV3Detail = HistoricalScenarioHistorySummary & {
  schema_version: 'historical-scenario-simulation-response-v3';
  baseline: PlannedPortfolioBaselineContext;
  result: HistoricalScenarioSimulationResponse;
};

export type AllocationHistoryV3Detail = AllocationHistorySummary & {
  schema_version: 'allocation-simulation-response-v3';
  baseline: PlannedPortfolioBaselineContext;
  result: AllocationSimulationResponse;
};

export type CombinedHistoryV3Detail = CombinedHistorySummary & {
  schema_version: 'combined-simulation-response-v3';
  baseline: PlannedPortfolioBaselineContext;
  result: CombinedSimulationResponse;
};

export type SimulationHistoryV3DetailResponse =
  | HistoricalScenarioHistoryV3Detail
  | AllocationHistoryV3Detail
  | CombinedHistoryV3Detail;

export type SimulationHistoryDetailResponse =
  | SimulationHistoryV1DetailResponse
  | SimulationHistoryV2DetailResponse
  | SimulationHistoryV3DetailResponse;

export function isSimulationHistoryV2(
  detail: SimulationHistoryDetailResponse
): detail is SimulationHistoryV2DetailResponse {
  return 'schema_version' in detail && detail.schema_version.endsWith('-v2');
}

export function isSimulationHistoryV3(
  detail: SimulationHistoryDetailResponse
): detail is SimulationHistoryV3DetailResponse {
  return 'schema_version' in detail && detail.schema_version.endsWith('-v3');
}
