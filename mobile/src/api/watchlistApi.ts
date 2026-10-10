import type { ApiCallOptions } from '../types/api';
import type {
  WatchlistCreateRequest,
  WatchlistItemResponse,
  WatchlistListResponse
} from '../types/watchlist';
import { apiRequest } from './apiClient';

export const watchlistApi = {
  list(options: ApiCallOptions = {}): Promise<WatchlistListResponse> {
    return apiRequest<WatchlistListResponse>('/api/watchlist', options);
  },

  add(
    symbol: string,
    options: ApiCallOptions = {}
  ): Promise<WatchlistItemResponse> {
    const request: WatchlistCreateRequest = { symbol };
    return apiRequest<WatchlistItemResponse, WatchlistCreateRequest>(
      '/api/watchlist',
      { ...options, method: 'POST', body: request }
    );
  },

  remove(symbol: string, options: ApiCallOptions = {}): Promise<void> {
    return apiRequest<void>(
      `/api/watchlist/${encodeURIComponent(symbol)}`,
      { ...options, method: 'DELETE', responseMode: 'none' }
    );
  }
};
