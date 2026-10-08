import { apiRequest } from './apiClient';
import type { ApiCallOptions } from '../types/api';
import type { AssetOutlookResponse, PortfolioOutlookResponse, WeeklyAssetOutlookResponse, WeeklyPortfolioOutlookResponse, WeeklyHorizon } from '../types/forecasting';

// These GET endpoints neither train models nor persist reports.
export function getAssetOutlook(symbol: string, options: ApiCallOptions = {}) {
  return apiRequest<AssetOutlookResponse>(`/api/forecasting/assets/${encodeURIComponent(symbol)}/outlook`, options);
}
export function getPortfolioOutlook(portfolioId: string, options: ApiCallOptions = {}) {
  return apiRequest<PortfolioOutlookResponse>(`/api/forecasting/portfolios/${encodeURIComponent(portfolioId)}/outlook`, options);
}
export function getWeeklyAssetOutlook(symbol: string, horizon: WeeklyHorizon, options: ApiCallOptions = {}) {
  return apiRequest<WeeklyAssetOutlookResponse>(`/api/forecasting/assets/${encodeURIComponent(symbol)}/horizons/${horizon}/outlook`, options);
}
export function getWeeklyPortfolioOutlook(portfolioId: string, horizon: WeeklyHorizon, options: ApiCallOptions = {}) {
  return apiRequest<WeeklyPortfolioOutlookResponse>(`/api/forecasting/portfolios/${encodeURIComponent(portfolioId)}/horizons/${horizon}/outlook`, options);
}
