import type { ApiCallOptions, Uuid } from '../types/api';
import type {
  AllocationSimulationRequest,
  AllocationSimulationResponse,
  CombinedSimulationRequest,
  CombinedSimulationResponse,
  HistoricalScenarioListResponse,
  HistoricalScenarioSimulationRequest,
  HistoricalScenarioSimulationResponse,
  SimulationHistoryDetailResponse,
  SimulationHistoryListResponse,
} from '../types/simulation';
import { apiRequest } from './apiClient';

function simulationsPath(portfolioId: Uuid): string {
  return `/api/portfolios/${encodeURIComponent(portfolioId)}/simulations`;
}

export function listHistoricalScenarios(
  signal?: AbortSignal,
): Promise<HistoricalScenarioListResponse> {
  return apiRequest<HistoricalScenarioListResponse>(
    '/api/simulations/historical-scenarios',
    { signal },
  );
}

export function runHistoricalScenario(
  portfolioId: Uuid,
  request: HistoricalScenarioSimulationRequest,
  options: ApiCallOptions = {},
): Promise<HistoricalScenarioSimulationResponse> {
  return apiRequest<
    HistoricalScenarioSimulationResponse,
    HistoricalScenarioSimulationRequest
  >(`${simulationsPath(portfolioId)}/historical-scenarios`, {
    ...options,
    method: 'POST',
    body: request,
  });
}

export function runAllocationSimulation(
  portfolioId: Uuid,
  request: AllocationSimulationRequest,
  options: ApiCallOptions = {},
): Promise<AllocationSimulationResponse> {
  return apiRequest<AllocationSimulationResponse, AllocationSimulationRequest>(
    `${simulationsPath(portfolioId)}/allocations`,
    { ...options, method: 'POST', body: request },
  );
}

export function runCombinedSimulation(
  portfolioId: Uuid,
  request: CombinedSimulationRequest,
  options: ApiCallOptions = {},
): Promise<CombinedSimulationResponse> {
  return apiRequest<CombinedSimulationResponse, CombinedSimulationRequest>(
    `${simulationsPath(portfolioId)}/combined`,
    { ...options, method: 'POST', body: request },
  );
}

export function listSimulationHistory(
  portfolioId: Uuid,
  options: ApiCallOptions = {},
): Promise<SimulationHistoryListResponse> {
  return apiRequest<SimulationHistoryListResponse>(
    simulationsPath(portfolioId),
    options,
  );
}

export function getSimulationHistory(
  portfolioId: Uuid,
  simulationId: Uuid,
  options: ApiCallOptions = {},
): Promise<SimulationHistoryDetailResponse> {
  return apiRequest<SimulationHistoryDetailResponse>(
    `${simulationsPath(portfolioId)}/${encodeURIComponent(simulationId)}`,
    options,
  );
}
