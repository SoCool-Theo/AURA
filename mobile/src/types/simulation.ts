import type { AnalysisPeriod, MaximumDrawdownMetrics } from './analytics';
import type { IsoDate, IsoDateTime, Uuid } from './api';
import type { PortfolioHoldingInput } from './portfolio';

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
  modified_allocation: PortfolioHoldingInput[];
};

export type CombinedSimulationRequest = HistoricalScenarioSimulationRequest & {
  modified_allocation: PortfolioHoldingInput[];
};

export type AllocationSimulationResult = {
  allocation: PortfolioHoldingInput[];
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

export type SimulationHistoryDetailResponse =
  | (HistoricalScenarioHistorySummary & {
    result: HistoricalScenarioSimulationResponse;
  })
  | (AllocationHistorySummary & {
    result: AllocationSimulationResponse;
  })
  | (CombinedHistorySummary & {
    result: CombinedSimulationResponse;
  });
