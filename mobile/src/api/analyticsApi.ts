import { environment } from '../config/environment';
import { analyticsMock } from '../mocks/analytics.mock';
import type { PortfolioAnalysis } from '../types/analytics';
import { apiClient } from './apiClient';

export const analyticsApi = {
  async analyze(portfolioId: string): Promise<PortfolioAnalysis> {
    if (environment.useMocks) return analyticsMock;
    return apiClient<PortfolioAnalysis>(`/api/portfolios/${portfolioId}/reports`, {
      method: 'POST',
      body: JSON.stringify({ start_date: '2025-01-01', end_date: '2026-01-01' })
    });
  }
};
