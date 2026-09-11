import type { AnalysisPeriod } from '../types/analytics';
import type { ApiCallOptions, Uuid } from '../types/api';
import type { PortfolioReportResponse } from '../types/report';
import { apiRequest } from './apiClient';

export const analyticsApi = {
  analyze(
    portfolioId: Uuid,
    period: AnalysisPeriod,
    options: ApiCallOptions = {}
  ): Promise<PortfolioReportResponse> {
    return apiRequest<PortfolioReportResponse, AnalysisPeriod>(
      `/api/portfolios/${encodeURIComponent(portfolioId)}/reports`,
      { ...options, method: 'POST', body: period }
    );
  }
};
