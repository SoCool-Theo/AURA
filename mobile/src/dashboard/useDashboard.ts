import { useCallback, useEffect, useRef, useState } from 'react';
import { useFocusEffect, useIsFocused } from '@react-navigation/native';

import { usePortfolios } from '../portfolio/usePortfolios';
import { useReports } from '../report/useReports';
import type { PortfolioResponse } from '../types/portfolio';
import type { PortfolioReportResponse } from '../types/report';
import type { ReportHistoryItem, ReportHistoryStatus } from '../report/ReportProvider';
import { ApiError } from '../api/apiClient';

export function useDashboard() {
  const portfoliosState = usePortfolios();
  const { getReport, getPortfolioReportHistory } = useReports();
  const { portfolios, activePortfolioId, selectPortfolio, getPortfolio, refreshPortfolios } = portfoliosState;
  const [history, setHistory] = useState<{ portfolioId: string; reports: ReportHistoryItem[] } | null>(null);
  const [historyStatus, setHistoryStatus] = useState<ReportHistoryStatus>('idle');
  const [historyError, setHistoryError] = useState<unknown>(null);
  const [historyRefreshing, setHistoryRefreshing] = useState(false);
  const focused = useIsFocused();
  const [revision, setRevision] = useState(0);
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);
  const [portfolioLoading, setPortfolioLoading] = useState(false);
  const [portfolioError, setPortfolioError] = useState<unknown>(null);
  const [report, setReport] = useState<PortfolioReportResponse | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState<unknown>(null);
  const refreshPending = useRef(false);
  const stateRef = useRef(portfoliosState);
  stateRef.current = portfoliosState;

  // Resolve against real list membership immediately, including after deletion.
  const selectedId = portfolios.find((item) => item.id === activePortfolioId)?.id
    ?? portfolios[0]?.id ?? null;
  useEffect(() => {
    if (selectedId && selectedId !== activePortfolioId) selectPortfolio(selectedId);
  }, [activePortfolioId, selectPortfolio, selectedId]);

  useFocusEffect(useCallback(() => {
    if (!stateRef.current.isRefreshing) void refreshPortfolios();
  }, [refreshPortfolios]));

  // Dashboard has an independent selected-history load, supplied by ReportProvider.
  // Global Reports failures cannot invalidate this portfolio's successful history.
  useEffect(() => {
    const selected = stateRef.current.portfolios.find((item) => item.id === selectedId);
    if (!focused || !selected) return;
    let current = true;
    setHistoryRefreshing(true);
    setHistoryStatus('loading');
    setHistoryError(null);
    void getPortfolioReportHistory(selected).then((reports) => {
      if (!current) return;
      setHistory({ portfolioId: selected.id, reports });
      setHistoryStatus('ready');
    }).catch((error: unknown) => {
      if (!current) return;
      setHistoryError(error);
      setHistoryStatus('error');
    }).finally(() => {
      if (current) setHistoryRefreshing(false);
    });
    return () => { current = false; };
  }, [focused, selectedId, getPortfolioReportHistory, revision]);

  useEffect(() => {
    if (!focused || !selectedId) return;
    let current = true;
    setPortfolioLoading(true);
    setPortfolioError(null);
    void getPortfolio(selectedId).then((value) => {
      if (current) setPortfolio(value);
    }).catch((error: unknown) => {
      if (current) {
        setPortfolioError(error);
        if (error instanceof ApiError && error.status === 404) setPortfolio(null);
      }
    }).finally(() => {
      if (current) setPortfolioLoading(false);
    });
    return () => { current = false; };
  }, [focused, getPortfolio, selectedId, revision]);

  // ReportProvider already orders by created_at descending with deterministic ties.
  const newest = history?.portfolioId === selectedId ? history.reports[0] : undefined;
  const newestId = newest?.id;
  useEffect(() => {
    if (!focused || !selectedId || !newestId || historyStatus !== 'ready') return;
    let current = true;
    setReportLoading(true);
    setReportError(null);
    void getReport(selectedId, newestId).then((value) => {
      if (current) setReport(value);
    }).catch((error: unknown) => {
      if (current) {
        setReportError(error);
        if (error instanceof ApiError && error.status === 404) setReport(null);
      }
    }).finally(() => {
      if (current) setReportLoading(false);
    });
    return () => { current = false; };
  }, [focused, getReport, historyStatus, newestId, selectedId, revision]);

  const refreshing = portfoliosState.isRefreshing || (Boolean(selectedId) && historyRefreshing)
    || (Boolean(selectedId) && portfolioLoading)
    || (historyStatus === 'ready' && Boolean(newestId) && reportLoading);

  async function refresh() {
    if (refreshPending.current || refreshing) return;
    refreshPending.current = true;
    try {
      await refreshPortfolios();
      setRevision((value) => value + 1);
    } finally {
      refreshPending.current = false;
    }
  }

  return {
    portfoliosState,
    reportsState: { historyStatus, historyError, isRefreshing: historyRefreshing },
    selectedId,
    portfolio: portfolio?.id === selectedId ? portfolio : null,
    portfolioLoading,
    portfolioError,
    report: historyStatus === 'ready' && report?.portfolio_id === selectedId && report.id === newestId ? report : null,
    reportLoading,
    reportError,
    newest,
    refreshing,
    refresh,
    retryDetails: () => setRevision((value) => value + 1)
  };
}
