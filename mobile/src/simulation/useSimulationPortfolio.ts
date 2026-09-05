import { useCallback, useEffect, useRef, useState } from 'react';

import { usePortfolios } from '../portfolio/usePortfolios';
import type { PortfolioResponse } from '../types/portfolio';

export function useSimulationPortfolio(requestedPortfolioId?: string) {
  const portfolioState = usePortfolios();
  const {
    activePortfolioId,
    portfolios,
    listStatus,
    getPortfolio,
    selectPortfolio
  } = portfolioState;
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<string | null>(
    requestedPortfolioId ?? activePortfolioId
  );
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);
  const [detailStatus, setDetailStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [detailError, setDetailError] = useState<unknown>(null);
  const detailRequestRef = useRef(0);

  useEffect(() => {
    if (selectedPortfolioId) return;
    const fallbackId = activePortfolioId ?? portfolios[0]?.id;
    if (fallbackId) setSelectedPortfolioId(fallbackId);
  }, [activePortfolioId, portfolios, selectedPortfolioId]);

  const loadPortfolio = useCallback(async (portfolioId: string) => {
    const requestId = detailRequestRef.current + 1;
    detailRequestRef.current = requestId;
    setDetailStatus('loading');
    setDetailError(null);
    setPortfolio(null);
    try {
      const response = await getPortfolio(portfolioId);
      if (detailRequestRef.current !== requestId) return;
      setPortfolio(response);
      setDetailStatus('ready');
    } catch (error) {
      if (detailRequestRef.current !== requestId) return;
      setDetailError(error);
      setDetailStatus('error');
    }
  }, [getPortfolio]);

  useEffect(() => {
    if (!selectedPortfolioId) {
      setPortfolio(null);
      setDetailStatus(listStatus === 'ready' ? 'ready' : 'idle');
      return;
    }
    void loadPortfolio(selectedPortfolioId);
    return () => {
      detailRequestRef.current += 1;
    };
  }, [listStatus, loadPortfolio, selectedPortfolioId]);

  const choosePortfolio = useCallback((portfolioId: string) => {
    setSelectedPortfolioId(portfolioId);
    selectPortfolio(portfolioId);
  }, [selectPortfolio]);

  return {
    ...portfolioState,
    selectedPortfolioId,
    portfolio,
    detailStatus,
    detailError,
    choosePortfolio,
    retryPortfolio: () => selectedPortfolioId
      ? loadPortfolio(selectedPortfolioId)
      : Promise.resolve()
  };
}
