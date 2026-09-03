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
import { useAuth } from '../auth/useAuth';
import type {
  PortfolioHoldingInput,
  PortfolioResponse,
  PortfolioSummaryResponse
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
  createPortfolioWithHoldings: (
    name: string,
    holdings: PortfolioHoldingInput[]
  ) => Promise<PortfolioResponse>;
  renamePortfolio: (
    portfolioId: string,
    name: string
  ) => Promise<PortfolioResponse>;
  replaceHoldings: (
    portfolioId: string,
    holdings: PortfolioHoldingInput[]
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
      setPortfolios(response.portfolios);
      setActivePortfolioId((current) => (
        current && response.portfolios.some((item) => item.id === current)
          ? current
          : response.portfolios[0]?.id ?? null
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
    upsertSummary(portfolio, false);
    return portfolio;
  }, [upsertSummary]);

  const createPortfolioWithHoldings = useCallback(async (
    name: string,
    holdings: PortfolioHoldingInput[]
  ) => {
    const created = await portfoliosApi.create({ name });
    upsertSummary(created, true);
    setActivePortfolioId(created.id);

    try {
      const completed = await portfoliosApi.replaceHoldings(created.id, {
        holdings
      });
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

  const replaceHoldings = useCallback(async (
    portfolioId: string,
    holdings: PortfolioHoldingInput[]
  ) => {
    const portfolio = await portfoliosApi.replaceHoldings(portfolioId, {
      holdings
    });
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
    createPortfolioWithHoldings,
    renamePortfolio,
    replaceHoldings,
    duplicatePortfolio,
    deletePortfolio
  }), [
    activePortfolioId,
    createPortfolioWithHoldings,
    deletePortfolio,
    duplicatePortfolio,
    getPortfolio,
    isRefreshing,
    listError,
    listStatus,
    portfolios,
    refreshPortfolios,
    renamePortfolio,
    replaceHoldings
  ]);

  return (
    <PortfolioContext.Provider value={value}>
      {children}
    </PortfolioContext.Provider>
  );
}
