import type { AnalysisPeriod } from '../types/analytics';
import type { ApiCallOptions, Uuid } from '../types/api';
import type { PortfolioCurrency } from '../types/portfolio';
import type { PortfolioReportResponse } from '../types/report';
import { apiRequest } from './apiClient';

export const analyticsApi = {
  analyze(
    portfolioId: Uuid,
    period: AnalysisPeriod,
    currency: PortfolioCurrency = 'USD',
    options: ApiCallOptions = {}
  ): Promise<PortfolioReportResponse> {
    return apiRequest<PortfolioReportResponse, AnalysisPeriod>(
      `/api/portfolios/${encodeURIComponent(portfolioId)}/reports?currency=${currency}`,
      { ...options, method: 'POST', body: period }
    );
  }
};
