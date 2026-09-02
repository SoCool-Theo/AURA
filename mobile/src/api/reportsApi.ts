import type { ApiCallOptions, Uuid } from '../types/api';
import type {
  PortfolioReportListResponse,
  PortfolioReportResponse
} from '../types/report';
import { apiRequest } from './apiClient';

function reportsPath(portfolioId: Uuid): string {
  return `/api/portfolios/${encodeURIComponent(portfolioId)}/reports`;
}

export const reportsApi = {
  list(
    portfolioId: Uuid,
    options: ApiCallOptions = {}
  ): Promise<PortfolioReportListResponse> {
    return apiRequest<PortfolioReportListResponse>(
      reportsPath(portfolioId),
      options
    );
  },

  get(
    portfolioId: Uuid,
    reportId: Uuid,
    options: ApiCallOptions = {}
  ): Promise<PortfolioReportResponse> {
    return apiRequest<PortfolioReportResponse>(
      `${reportsPath(portfolioId)}/${encodeURIComponent(reportId)}`,
      options
    );
  },

  delete(
    portfolioId: Uuid,
    reportId: Uuid,
    options: ApiCallOptions = {}
  ): Promise<void> {
    return apiRequest<void>(
      `${reportsPath(portfolioId)}/${encodeURIComponent(reportId)}`,
      { ...options, method: 'DELETE', responseMode: 'none' }
    );
  }
};
