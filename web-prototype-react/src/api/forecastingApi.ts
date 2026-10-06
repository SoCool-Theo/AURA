import { apiRequest } from './apiClient';
import type { ApiCallOptions } from '../types/api';
import type { AssetOutlookResponse, PortfolioOutlookResponse } from '../types/forecasting';

// These GET endpoints neither train models nor persist reports.
export function getAssetOutlook(symbol: string, options: ApiCallOptions = {}) {
  return apiRequest<AssetOutlookResponse>(`/api/forecasting/assets/${encodeURIComponent(symbol)}/outlook`, options);
}
export function getPortfolioOutlook(portfolioId: string, options: ApiCallOptions = {}) {
  return apiRequest<PortfolioOutlookResponse>(`/api/forecasting/portfolios/${encodeURIComponent(portfolioId)}/outlook`, options);
}
