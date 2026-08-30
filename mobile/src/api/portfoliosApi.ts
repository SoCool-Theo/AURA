import { environment } from '../config/environment';
import { portfoliosMock } from '../mocks/portfolios.mock';
import type { Portfolio } from '../types/portfolio';
import { apiClient } from './apiClient';

export const portfoliosApi = {
  async list(): Promise<Portfolio[]> {
    if (environment.useMocks) return portfoliosMock;
    const response = await apiClient<{ items: Portfolio[] }>('/api/portfolios');
    return response.items;
  },

  async get(portfolioId: string): Promise<Portfolio> {
    if (environment.useMocks) {
      const found = portfoliosMock.find((p) => p.id === portfolioId);
      if (!found) throw new Error('Portfolio not found');
      return found;
    }
    return apiClient<Portfolio>(`/api/portfolios/${portfolioId}`);
  }
};
