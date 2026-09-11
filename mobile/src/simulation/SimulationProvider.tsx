import React, {
  createContext,
  PropsWithChildren,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from 'react';

import { simulationsApi } from '../api/simulationsApi';
import { useAuth } from '../auth/useAuth';
import type { PortfolioSummaryResponse } from '../types/portfolio';
import type {
  AllocationSimulationRequest,
  AllocationSimulationResponse,
  CombinedSimulationRequest,
  CombinedSimulationResponse,
  HistoricalScenarioResponse,
  HistoricalScenarioSimulationResponse,
  SimulationHistoryDetailResponse,
  SimulationHistorySummary
} from '../types/simulation';

export type SimulationRunResult =
  | { type: 'historical-scenario'; response: HistoricalScenarioSimulationResponse }
  | { type: 'allocation'; response: AllocationSimulationResponse }
  | { type: 'combined'; response: CombinedSimulationResponse };

export type GlobalSimulationHistoryItem = SimulationHistorySummary & {
  portfolio_name: string;
};

export type LoadStatus = 'idle' | 'loading' | 'ready' | 'error';

type SimulationContextValue = {
  scenarios: HistoricalScenarioResponse[];
  scenarioStatus: LoadStatus;
  scenarioError: unknown;
  refreshScenarios: () => Promise<void>;
  history: GlobalSimulationHistoryItem[];
  historyStatus: LoadStatus;
  historyError: unknown;
  isRefreshingHistory: boolean;
  refreshHistory: (portfolios: PortfolioSummaryResponse[]) => Promise<void>;
  runHistorical: (
    portfolioId: string,
    scenarioId: string
  ) => Promise<HistoricalScenarioSimulationResponse>;
  runAllocation: (
    portfolioId: string,
    request: AllocationSimulationRequest
  ) => Promise<AllocationSimulationResponse>;
  runCombined: (
    portfolioId: string,
    request: CombinedSimulationRequest
  ) => Promise<CombinedSimulationResponse>;
  getHistoryDetail: (
    portfolioId: string,
    simulationId: string
  ) => Promise<SimulationHistoryDetailResponse>;
};

export const SimulationContext = createContext<SimulationContextValue | undefined>(
  undefined
);

function orderGlobalHistory(
  history: GlobalSimulationHistoryItem[]
): GlobalSimulationHistoryItem[] {
  return [...history].sort((left, right) => {
    const leftTimestamp = Date.parse(left.created_at);
    const rightTimestamp = Date.parse(right.created_at);
    if (
      Number.isFinite(leftTimestamp)
      && Number.isFinite(rightTimestamp)
      && leftTimestamp !== rightTimestamp
    ) {
      return rightTimestamp - leftTimestamp;
    }
    const timestampOrder = right.created_at.localeCompare(left.created_at);
    if (timestampOrder) return timestampOrder;
    const portfolioOrder = left.portfolio_id.localeCompare(right.portfolio_id);
    return portfolioOrder || left.id.localeCompare(right.id);
  });
}

export function SimulationProvider({ children }: PropsWithChildren) {
  const { status: authStatus, user } = useAuth();
  const [scenarios, setScenarios] = useState<HistoricalScenarioResponse[]>([]);
  const [scenarioStatus, setScenarioStatus] = useState<LoadStatus>('idle');
  const [scenarioError, setScenarioError] = useState<unknown>(null);
  const [history, setHistory] = useState<GlobalSimulationHistoryItem[]>([]);
  const [historyStatus, setHistoryStatus] = useState<LoadStatus>('idle');
  const [historyError, setHistoryError] = useState<unknown>(null);
  const [isRefreshingHistory, setIsRefreshingHistory] = useState(false);
  const scenarioRequestRef = useRef(0);
  const historyRequestRef = useRef(0);

  const refreshScenarios = useCallback(async (): Promise<void> => {
    const requestId = scenarioRequestRef.current + 1;
    scenarioRequestRef.current = requestId;
    setScenarioStatus('loading');
    setScenarioError(null);
    try {
      const response = await simulationsApi.listHistoricalScenarios();
      if (scenarioRequestRef.current !== requestId) return;
      setScenarios(response.scenarios);
      setScenarioStatus('ready');
    } catch (error) {
      if (scenarioRequestRef.current !== requestId) return;
      setScenarioError(error);
      setScenarioStatus('error');
    }
  }, []);

  useEffect(() => {
    void refreshScenarios();
    return () => {
      scenarioRequestRef.current += 1;
    };
  }, [refreshScenarios]);

  const refreshHistory = useCallback(async (
    portfolios: PortfolioSummaryResponse[]
  ): Promise<void> => {
    const requestId = historyRequestRef.current + 1;
    historyRequestRef.current = requestId;
    setIsRefreshingHistory(true);
    setHistoryError(null);
    setHistoryStatus((current) => current === 'ready' ? 'ready' : 'loading');
    try {
      const histories = await Promise.all(portfolios.map(async (portfolio) => ({
        portfolio,
        response: await simulationsApi.history(portfolio.id)
      })));
      if (historyRequestRef.current !== requestId) return;
      setHistory(orderGlobalHistory(histories.flatMap(({ portfolio, response }) => (
        response.simulations.map((simulation) => ({
          ...simulation,
          portfolio_name: portfolio.name
        }))
      ))));
      setHistoryStatus('ready');
    } catch (error) {
      if (historyRequestRef.current !== requestId) return;
      setHistoryError(error);
      setHistoryStatus('error');
    } finally {
      if (historyRequestRef.current === requestId) setIsRefreshingHistory(false);
    }
  }, []);

  useEffect(() => {
    historyRequestRef.current += 1;
    setHistory([]);
    setHistoryStatus('idle');
    setHistoryError(null);
    setIsRefreshingHistory(false);
  }, [authStatus, user?.id]);

  const invalidateHistory = useCallback(() => {
    historyRequestRef.current += 1;
    setHistoryStatus('idle');
    setHistoryError(null);
    setIsRefreshingHistory(false);
  }, []);

  const runHistorical = useCallback(async (
    portfolioId: string,
    scenarioId: string
  ) => {
    const response = await simulationsApi.runHistorical(portfolioId, {
      scenario_id: scenarioId
    });
    invalidateHistory();
    return response;
  }, [invalidateHistory]);

  const runAllocation = useCallback(async (
    portfolioId: string,
    request: AllocationSimulationRequest
  ) => {
    const response = await simulationsApi.runAllocation(portfolioId, request);
    invalidateHistory();
    return response;
  }, [invalidateHistory]);

  const runCombined = useCallback(async (
    portfolioId: string,
    request: CombinedSimulationRequest
  ) => {
    const response = await simulationsApi.runCombined(portfolioId, request);
    invalidateHistory();
    return response;
  }, [invalidateHistory]);

  const getHistoryDetail = useCallback((
    portfolioId: string,
    simulationId: string
  ) => simulationsApi.getHistory(portfolioId, simulationId), []);

  const value = useMemo<SimulationContextValue>(() => ({
    scenarios,
    scenarioStatus,
    scenarioError,
    refreshScenarios,
    history,
    historyStatus,
    historyError,
    isRefreshingHistory,
    refreshHistory,
    runHistorical,
    runAllocation,
    runCombined,
    getHistoryDetail
  }), [
    getHistoryDetail,
    history,
    historyError,
    historyStatus,
    isRefreshingHistory,
    refreshHistory,
    refreshScenarios,
    runAllocation,
    runCombined,
    runHistorical,
    scenarioError,
    scenarios,
    scenarioStatus
  ]);

  return (
    <SimulationContext.Provider value={value}>
      {children}
    </SimulationContext.Provider>
  );
}
