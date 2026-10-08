import React, {
  createContext,
  PropsWithChildren,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from 'react';

import { portfoliosApi } from '../api/portfoliosApi';
import { ApiError } from '../api/apiClient';
import { useAuth } from '../auth/useAuth';
import type {
  PortfolioCurrency,
  PortfolioPlannedAllocationResponse,
  PortfolioPlannedHoldingInput,
  PortfolioPlannedPreviewResponse,
  PortfolioRealHoldingInput,
  PortfolioResponse,
  PortfolioSummaryResponse,
  PortfolioValuationResponse
} from '../types/portfolio';
import { PortfolioCreatedWithoutHoldingsError } from './portfolioErrors';

export type PortfolioListStatus = 'idle' | 'loading' | 'ready' | 'error';

type PortfolioContextValue = {
  portfolios: PortfolioSummaryResponse[];
  activePortfolioId: string | null;
  listStatus: PortfolioListStatus;
  listError: unknown;
  isRefreshing: boolean;
  refreshPortfolios: () => Promise<void>;
  selectPortfolio: (portfolioId: string) => void;
  getPortfolio: (portfolioId: string) => Promise<PortfolioResponse>;
  getPortfolioValuation: (
    portfolioId: string,
    currency?: PortfolioCurrency
  ) => Promise<PortfolioValuationResponse>;
  getPlannedAllocation: (portfolioId: string) => Promise<PortfolioPlannedAllocationResponse>;
  getPlannedPreview: (portfolioId: string) => Promise<PortfolioPlannedPreviewResponse>;
  createPortfolioWithRealHoldings: (
    name: string,
    holdings: PortfolioRealHoldingInput[]
  ) => Promise<PortfolioResponse>;
  createPortfolioWithPlannedHoldings: (
    name: string,
    planCurrency: PortfolioCurrency,
    holdings: PortfolioPlannedHoldingInput[]
  ) => Promise<PortfolioResponse>;
  renamePortfolio: (
    portfolioId: string,
    name: string
  ) => Promise<PortfolioResponse>;
  replaceRealHoldings: (
    portfolioId: string,
    holdings: PortfolioRealHoldingInput[]
  ) => Promise<PortfolioResponse>;
  replacePlannedHoldings: (
    portfolioId: string,
    holdings: PortfolioPlannedHoldingInput[]
  ) => Promise<PortfolioResponse>;
  duplicatePortfolio: (
    portfolioId: string,
    name: string
  ) => Promise<PortfolioResponse>;
  deletePortfolio: (portfolioId: string) => Promise<void>;
};

export const PortfolioContext = createContext<PortfolioContextValue | undefined>(
  undefined
);

function toSummary(portfolio: PortfolioResponse): PortfolioSummaryResponse {
  return {
    id: portfolio.id,
    name: portfolio.name,
    portfolio_type: portfolio.portfolio_type,
    plan_currency: portfolio.plan_currency,
    created_at: portfolio.created_at,
    updated_at: portfolio.updated_at
  };
}

export function PortfolioProvider({ children }: PropsWithChildren) {
  const { status: authStatus, user } = useAuth();
  const [portfolios, setPortfolios] = useState<PortfolioSummaryResponse[]>([]);
  const [activePortfolioId, setActivePortfolioId] = useState<string | null>(null);
  const [listStatus, setListStatus] = useState<PortfolioListStatus>('idle');
  const [listError, setListError] = useState<unknown>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const listRequestRef = useRef(0);
  const deletedPortfolioIdsRef = useRef(new Set<string>());

  const upsertSummary = useCallback((
    portfolio: PortfolioResponse,
    prepend: boolean
  ) => {
    const summary = toSummary(portfolio);
    setPortfolios((current) => {
      const withoutCurrent = current.filter((item) => item.id !== summary.id);
      if (prepend) return [summary, ...withoutCurrent];

      const existingIndex = current.findIndex((item) => item.id === summary.id);
      if (existingIndex < 0) return [...current, summary];
      const next = [...current];
      next[existingIndex] = summary;
      return next;
    });
  }, []);

  const refreshPortfolios = useCallback(async (): Promise<void> => {
    const requestId = listRequestRef.current + 1;
    listRequestRef.current = requestId;
    setIsRefreshing(true);
    setListError(null);
    setListStatus((current) => current === 'ready' ? 'ready' : 'loading');

    try {
      const response = await portfoliosApi.list();
      if (listRequestRef.current !== requestId) return;
      const available = response.portfolios.filter((item) => !deletedPortfolioIdsRef.current.has(item.id));
      setPortfolios(available);
      setActivePortfolioId((current) => (
        current && available.some((item) => item.id === current)
          ? current
          : available[0]?.id ?? null
      ));
      setListStatus('ready');
    } catch (error) {
      if (listRequestRef.current !== requestId) return;
      setListError(error);
      setListStatus('error');
    } finally {
      if (listRequestRef.current === requestId) setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    deletedPortfolioIdsRef.current.clear();
    listRequestRef.current += 1;
    if (authStatus !== 'authenticated') {
      setPortfolios([]);
      setActivePortfolioId(null);
      setListStatus('idle');
      setListError(null);
      setIsRefreshing(false);
      return;
    }
    void refreshPortfolios();
  }, [authStatus, refreshPortfolios, user?.id]);

  const getPortfolio = useCallback(async (portfolioId: string) => {
    const portfolio = await portfoliosApi.get(portfolioId);
    if (deletedPortfolioIdsRef.current.has(portfolioId)) {
      throw new ApiError({ kind: 'http', status: 404, message: 'Portfolio not found.' });
    }
    upsertSummary(portfolio, false);
    return portfolio;
  }, [upsertSummary]);

  const getPortfolioValuation = useCallback((
    portfolioId: string,
    currency: PortfolioCurrency = 'USD'
  ) => portfoliosApi.getValuation(portfolioId, currency), []);

  const getPlannedAllocation = useCallback(
    (portfolioId: string) => portfoliosApi.getPlannedAllocation(portfolioId),
    []
  );

  const getPlannedPreview = useCallback(
    (portfolioId: string) => portfoliosApi.getPlannedPreview(portfolioId),
    []
  );

  const createPortfolioWithRealHoldings = useCallback(async (
    name: string,
    holdings: PortfolioRealHoldingInput[]
  ) => {
    const created = await portfoliosApi.create({ name, portfolio_type: 'CURRENT' });
    upsertSummary(created, true);
    setActivePortfolioId(created.id);

    try {
      const completed = await portfoliosApi.replaceRealHoldings(
        created.id,
        holdings
      );
      upsertSummary(completed, false);
      return completed;
    } catch (error) {
      throw new PortfolioCreatedWithoutHoldingsError(created, error);
    }
  }, [upsertSummary]);

  const createPortfolioWithPlannedHoldings = useCallback(async (
    name: string,
    planCurrency: PortfolioCurrency,
    holdings: PortfolioPlannedHoldingInput[]
  ) => {
    const created = await portfoliosApi.create({
      name,
      portfolio_type: 'PLANNED',
      plan_currency: planCurrency
    });
    upsertSummary(created, true);
    setActivePortfolioId(created.id);
    try {
      const completed = await portfoliosApi.replacePlannedHoldings(
        created.id,
        holdings
      );
      upsertSummary(completed, false);
      return completed;
    } catch (error) {
      throw new PortfolioCreatedWithoutHoldingsError(created, error);
    }
  }, [upsertSummary]);

  const renamePortfolio = useCallback(async (
    portfolioId: string,
    name: string
  ) => {
    const portfolio = await portfoliosApi.update(portfolioId, { name });
    upsertSummary(portfolio, false);
    return portfolio;
  }, [upsertSummary]);

  const replaceRealHoldings = useCallback(async (
    portfolioId: string,
    holdings: PortfolioRealHoldingInput[]
  ) => {
    const portfolio = await portfoliosApi.replaceRealHoldings(
      portfolioId,
      holdings
    );
    upsertSummary(portfolio, false);
    return portfolio;
  }, [upsertSummary]);

  const replacePlannedHoldings = useCallback(async (
    portfolioId: string,
    holdings: PortfolioPlannedHoldingInput[]
  ) => {
    const portfolio = await portfoliosApi.replacePlannedHoldings(
      portfolioId,
      holdings
    );
    upsertSummary(portfolio, false);
    return portfolio;
  }, [upsertSummary]);

  const duplicatePortfolio = useCallback(async (
    portfolioId: string,
    name: string
  ) => {
    const portfolio = await portfoliosApi.duplicate(portfolioId, { name });
    upsertSummary(portfolio, true);
    setActivePortfolioId(portfolio.id);
    return portfolio;
  }, [upsertSummary]);

  const deletePortfolio = useCallback(async (portfolioId: string) => {
    await portfoliosApi.delete(portfolioId);
    deletedPortfolioIdsRef.current.add(portfolioId);
    setPortfolios((current) => current.filter((item) => item.id !== portfolioId));
    setActivePortfolioId((current) => current === portfolioId ? null : current);
  }, []);

  const value = useMemo<PortfolioContextValue>(() => ({
    portfolios,
    activePortfolioId,
    listStatus,
    listError,
    isRefreshing,
    refreshPortfolios,
    selectPortfolio: setActivePortfolioId,
    getPortfolio,
    getPortfolioValuation,
    getPlannedAllocation,
    getPlannedPreview,
    createPortfolioWithRealHoldings,
    createPortfolioWithPlannedHoldings,
    renamePortfolio,
    replaceRealHoldings,
    replacePlannedHoldings,
    duplicatePortfolio,
    deletePortfolio
  }), [
    activePortfolioId,
    createPortfolioWithRealHoldings,
    createPortfolioWithPlannedHoldings,
    deletePortfolio,
    duplicatePortfolio,
    getPortfolio,
    getPortfolioValuation,
    getPlannedAllocation,
    getPlannedPreview,
    isRefreshing,
    listError,
    listStatus,
    portfolios,
    refreshPortfolios,
    renamePortfolio,
    replacePlannedHoldings,
    replaceRealHoldings
  ]);

  return (
    <PortfolioContext.Provider value={value}>
      {children}
    </PortfolioContext.Provider>
  );
}
