import { environment } from '../config/environment';
import type { SimulationRecord } from '../types/simulation';
import { apiClient } from './apiClient';

export const simulationsApi = {
  async history(portfolioId: string): Promise<SimulationRecord[]> {
    if (environment.useMocks) return [];
    const response = await apiClient<{ items: SimulationRecord[] }>(
      `/api/portfolios/${portfolioId}/simulations`
    );
    return response.items;
  }
};
