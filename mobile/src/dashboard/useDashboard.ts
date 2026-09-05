import { useCallback, useEffect, useRef, useState } from 'react';
import { useFocusEffect, useIsFocused } from '@react-navigation/native';

import { usePortfolios } from '../portfolio/usePortfolios';
import { useReports } from '../report/useReports';
import type { PortfolioResponse } from '../types/portfolio';
import type { PortfolioReportResponse } from '../types/report';

export function useDashboard() {
  const portfoliosState = usePortfolios();
  const reportsState = useReports();
  const { portfolios, activePortfolioId, selectPortfolio, getPortfolio, refreshPortfolios } = portfoliosState;
  const { reports, historyStatus, getReport, refreshReportHistory } = reportsState;
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

  // Membership, not array identity: getPortfolio updates provider summaries.
  // Depending on the array itself would repeatedly reload after those updates.
  const portfolioIds = JSON.stringify(portfolios.map((item) => item.id));
  useEffect(() => {
    if (focused && (stateRef.current.listStatus === 'ready' || stateRef.current.portfolios.length)) {
      void refreshReportHistory(stateRef.current.portfolios);
    }
  }, [focused, portfolioIds, refreshReportHistory, revision, portfoliosState.listStatus]);

  useEffect(() => {
    if (!focused || !selectedId) return;
    let current = true;
    setPortfolioLoading(true);
    setPortfolioError(null);
    void getPortfolio(selectedId).then((value) => {
      if (current) setPortfolio(value);
    }).catch((error: unknown) => {
      if (current) setPortfolioError(error);
    }).finally(() => {
      if (current) setPortfolioLoading(false);
    });
    return () => { current = false; };
  }, [focused, getPortfolio, selectedId, revision]);

  // ReportProvider already orders by created_at descending with deterministic ties.
  const newest = reports.find((item) => item.portfolio_id === selectedId);
  const newestId = newest?.id;
  useEffect(() => {
    if (!focused || !selectedId || !newestId || historyStatus !== 'ready') return;
    let current = true;
    setReportLoading(true);
    setReportError(null);
    void getReport(selectedId, newestId).then((value) => {
      if (current) setReport(value);
    }).catch((error: unknown) => {
      if (current) setReportError(error);
    }).finally(() => {
      if (current) setReportLoading(false);
    });
    return () => { current = false; };
  }, [focused, getReport, historyStatus, newestId, selectedId, revision]);

  const refreshing = portfoliosState.isRefreshing || reportsState.isRefreshing
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
    reportsState,
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
