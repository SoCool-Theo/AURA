import { apiRequest } from './apiClient';
import type { ApiCallOptions } from '../types/api';
import type { MarketDataStatusResponse } from '../types/marketData';

// Read persisted status only. Customers never trigger provider downloads.
export function getMarketDataStatus(options: ApiCallOptions = {}): Promise<MarketDataStatusResponse> {
  return apiRequest<MarketDataStatusResponse>('/api/market-data/status', options);
}
