import { useCallback, useEffect, useRef, useState } from 'react';

import { usePortfolios } from '../portfolio/usePortfolios';
import {
  portfolioHoldingMode,
  type PortfolioPlannedAllocationResponse,
  type PortfolioResponse,
  type PortfolioValuationResponse
} from '../types/portfolio';

export function useSimulationPortfolio(requestedPortfolioId?: string) {
  const portfolioState = usePortfolios();
  const {
    activePortfolioId,
    portfolios,
    listStatus,
    getPortfolio,
    getPortfolioValuation,
    getPlannedAllocation,
    selectPortfolio
  } = portfolioState;
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<string | null>(
    requestedPortfolioId ?? activePortfolioId
  );
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);
  const [detailStatus, setDetailStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [detailError, setDetailError] = useState<unknown>(null);
  const [valuation, setValuation] = useState<PortfolioValuationResponse | null>(null);
  const [plannedAllocation, setPlannedAllocation] = useState<PortfolioPlannedAllocationResponse | null>(null);
  const [valuationStatus, setValuationStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [valuationError, setValuationError] = useState<unknown>(null);
  const detailRequestRef = useRef(0);

  useEffect(() => {
    if (listStatus !== 'ready' || portfolios.some((item) => item.id === selectedPortfolioId)) return;
    const fallbackId = portfolios.find((item) => item.id === activePortfolioId)?.id ?? portfolios[0]?.id ?? null;
    setSelectedPortfolioId(fallbackId);
    if (fallbackId) selectPortfolio(fallbackId);
  }, [activePortfolioId, listStatus, portfolios, selectedPortfolioId, selectPortfolio]);

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

  const selectedPortfolio = portfolio?.id === selectedPortfolioId
    ? portfolio
    : null;

  useEffect(() => {
    if (!selectedPortfolio) {
      setValuation(null);
      setPlannedAllocation(null);
      setValuationStatus('idle');
      setValuationError(null);
      return;
    }
    if (selectedPortfolio.portfolio_type === 'PLANNED' && selectedPortfolio.holdings.length) {
      let current = true;
      setValuation(null);
      setPlannedAllocation(null);
      setValuationStatus('loading');
      setValuationError(null);
      void getPlannedAllocation(selectedPortfolio.id).then((response) => {
        if (!current) return;
        setPlannedAllocation(response);
        setValuationStatus('ready');
      }).catch((error: unknown) => {
        if (!current) return;
        setValuationError(error);
        setValuationStatus('error');
      });
      return () => { current = false; };
    }
    if (portfolioHoldingMode(selectedPortfolio.holdings) !== 'real') {
      setValuation(null);
      setPlannedAllocation(null);
      setValuationStatus('idle');
      setValuationError(null);
      return;
    }

    let current = true;
    setValuation(null);
    setPlannedAllocation(null);
    setValuationStatus('loading');
    setValuationError(null);
    void getPortfolioValuation(selectedPortfolio.id, 'USD').then((response) => {
      if (!current) return;
      setValuation(response);
      setValuationStatus('ready');
    }).catch((error: unknown) => {
      if (!current) return;
      setValuationError(error);
      setValuationStatus('error');
    });
    return () => { current = false; };
  }, [getPlannedAllocation, getPortfolioValuation, selectedPortfolio]);

  const choosePortfolio = useCallback((portfolioId: string) => {
    setSelectedPortfolioId(portfolioId);
    selectPortfolio(portfolioId);
  }, [selectPortfolio]);

  return {
    ...portfolioState,
    selectedPortfolioId,
    portfolio: selectedPortfolio,
    detailStatus,
    detailError,
    valuation: valuation?.portfolio_id === selectedPortfolio?.id
      ? valuation
      : null,
    plannedAllocation: plannedAllocation?.portfolio_id === selectedPortfolio?.id
      ? plannedAllocation
      : null,
    valuationStatus,
    valuationError,
    choosePortfolio,
    retryPortfolio: () => selectedPortfolioId
      ? loadPortfolio(selectedPortfolioId)
      : Promise.resolve()
  };
}
