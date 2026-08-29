import type { AnalysisPeriod } from '../types/analytics';
import type { ApiCallOptions, Uuid } from '../types/api';
import type {
  PortfolioReportListResponse,
  PortfolioReportResponse,
} from '../types/report';
import { apiRequest } from './apiClient';

function reportsPath(portfolioId: Uuid): string {
  return `/api/portfolios/${encodeURIComponent(portfolioId)}/reports`;
}

export function createPortfolioReport(
  portfolioId: Uuid,
  period: AnalysisPeriod,
  options: ApiCallOptions = {},
): Promise<PortfolioReportResponse> {
  return apiRequest<PortfolioReportResponse, AnalysisPeriod>(
    reportsPath(portfolioId),
    { ...options, method: 'POST', body: period },
  );
}

export function listPortfolioReports(
  portfolioId: Uuid,
  options: ApiCallOptions = {},
): Promise<PortfolioReportListResponse> {
  return apiRequest<PortfolioReportListResponse>(
    reportsPath(portfolioId),
    options,
  );
}

export function getPortfolioReport(
  portfolioId: Uuid,
  reportId: Uuid,
  options: ApiCallOptions = {},
): Promise<PortfolioReportResponse> {
  return apiRequest<PortfolioReportResponse>(
    `${reportsPath(portfolioId)}/${encodeURIComponent(reportId)}`,
    options,
  );
}
