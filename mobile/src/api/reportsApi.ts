import { environment } from '../config/environment';
import type { ReportSnapshot } from '../types/report';
import { apiClient } from './apiClient';

export const reportsApi = {
  async list(portfolioId: string): Promise<ReportSnapshot[]> {
    if (environment.useMocks) return [];
    const response = await apiClient<{ items: ReportSnapshot[] }>(
      `/api/portfolios/${portfolioId}/reports`
    );
    return response.items;
  },

  async get(portfolioId: string, reportId: string): Promise<ReportSnapshot> {
    return apiClient<ReportSnapshot>(
      `/api/portfolios/${portfolioId}/reports/${reportId}`
    );
  }
};
