import React, {
  createContext,
  PropsWithChildren,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from 'react';

import { analyticsApi } from '../api/analyticsApi';
import { reportsApi } from '../api/reportsApi';
import { useAuth } from '../auth/useAuth';
import type { AnalysisPeriod } from '../types/analytics';
import type {
  PortfolioCurrency,
  PortfolioSummaryResponse
} from '../types/portfolio';
import type {
  PortfolioReportResponse,
  PortfolioReportSummary
} from '../types/report';

export type ReportHistoryItem = PortfolioReportSummary & {
  portfolio_name: string;
};

export type ReportHistoryStatus = 'idle' | 'loading' | 'ready' | 'error';

type ReportContextValue = {
  getPortfolioReportHistory: (portfolio: PortfolioSummaryResponse) => Promise<ReportHistoryItem[]>;
  reports: ReportHistoryItem[];
  historyStatus: ReportHistoryStatus;
  historyError: unknown;
  isRefreshing: boolean;
  refreshReportHistory: (
    portfolios: PortfolioSummaryResponse[]
  ) => Promise<void>;
  createReport: (
    portfolioId: string,
    period: AnalysisPeriod,
    currency?: PortfolioCurrency
  ) => Promise<PortfolioReportResponse>;
  getReport: (
    portfolioId: string,
    reportId: string
  ) => Promise<PortfolioReportResponse>;
  deleteReport: (portfolioId: string, reportId: string) => Promise<void>;
};

export const ReportContext = createContext<ReportContextValue | undefined>(
  undefined
);

function reportSummary(
  report: PortfolioReportResponse
): ReportHistoryItem {
  return {
    id: report.id,
    portfolio_id: report.portfolio_id,
    portfolio_name: report.analysis.portfolio_name,
    start_date: report.analysis.start_date,
    end_date: report.analysis.end_date,
    created_at: report.created_at
  };
}

function orderGlobalHistory(
  reports: ReportHistoryItem[]
): ReportHistoryItem[] {
  return [...reports].sort((left, right) => {
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

export function ReportProvider({ children }: PropsWithChildren) {
  const { status: authStatus, user } = useAuth();
  const [reports, setReports] = useState<ReportHistoryItem[]>([]);
  const [historyStatus, setHistoryStatus] = useState<ReportHistoryStatus>('idle');
  const [historyError, setHistoryError] = useState<unknown>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const historyRequestRef = useRef(0);
  const deletedReportIdsRef = useRef(new Set<string>());

  // One transport and ordering path for both selected and global history views.
  const getPortfolioReportHistory = useCallback(async (portfolio: PortfolioSummaryResponse) => {
    const response = await reportsApi.list(portfolio.id);
    return orderGlobalHistory(response.reports.filter((report) => !deletedReportIdsRef.current.has(report.id)).map((report) => ({
      ...report,
      portfolio_name: portfolio.name
    })));
  }, []);

  const refreshReportHistory = useCallback(async (
    portfolios: PortfolioSummaryResponse[]
  ): Promise<void> => {
    const requestId = historyRequestRef.current + 1;
    historyRequestRef.current = requestId;
    setIsRefreshing(true);
    setHistoryError(null);
    setHistoryStatus((current) => current === 'ready' ? 'ready' : 'loading');

    try {
      const histories = await Promise.all(portfolios.map(getPortfolioReportHistory));
      if (historyRequestRef.current !== requestId) return;

      setReports(orderGlobalHistory(histories.flat().filter((report) => !deletedReportIdsRef.current.has(report.id))));
      setHistoryStatus('ready');
    } catch (error) {
      if (historyRequestRef.current !== requestId) return;
      setHistoryError(error);
      setHistoryStatus('error');
    } finally {
      if (historyRequestRef.current === requestId) setIsRefreshing(false);
    }
  }, [getPortfolioReportHistory]);

  useEffect(() => {
    deletedReportIdsRef.current.clear();
    historyRequestRef.current += 1;
    setReports([]);
    setHistoryStatus('idle');
    setHistoryError(null);
    setIsRefreshing(false);
  }, [authStatus, user?.id]);

  const createReport = useCallback(async (
    portfolioId: string,
    period: AnalysisPeriod,
    currency: PortfolioCurrency = 'USD'
  ) => {
    const report = await analyticsApi.analyze(portfolioId, period, currency);
    const summary = reportSummary(report);
    setReports((current) => orderGlobalHistory([
      summary,
      ...current.filter((item) => item.id !== summary.id)
    ]));
    return report;
  }, []);

  const getReport = useCallback((portfolioId: string, reportId: string) => (
    reportsApi.get(portfolioId, reportId)
  ), []);

  const deleteReport = useCallback(async (
    portfolioId: string,
    reportId: string
  ) => {
    await reportsApi.delete(portfolioId, reportId);
    deletedReportIdsRef.current.add(reportId);
    setReports((current) => current.filter((item) => item.id !== reportId));
  }, []);

  const value = useMemo<ReportContextValue>(() => ({
    getPortfolioReportHistory,
    reports,
    historyStatus,
    historyError,
    isRefreshing,
    refreshReportHistory,
    createReport,
    getReport,
    deleteReport
  }), [
    getPortfolioReportHistory,
    createReport,
    deleteReport,
    getReport,
    historyError,
    historyStatus,
    isRefreshing,
    refreshReportHistory,
    reports
  ]);

  return (
    <ReportContext.Provider value={value}>
      {children}
    </ReportContext.Provider>
  );
}
