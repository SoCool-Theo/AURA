import type { ApiCallOptions, Uuid } from '../types/api';
import type {
  PortfolioCreateRequest,
  PortfolioDuplicateRequest,
  PortfolioHoldingsReplaceRequest,
  PortfolioListResponse,
  PortfolioResponse,
  PortfolioUpdateRequest
} from '../types/portfolio';
import { apiRequest } from './apiClient';

function portfolioPath(portfolioId: Uuid): string {
  return `/api/portfolios/${encodeURIComponent(portfolioId)}`;
}

export const portfoliosApi = {
  create(
    request: PortfolioCreateRequest,
    options: ApiCallOptions = {}
  ): Promise<PortfolioResponse> {
    return apiRequest<PortfolioResponse, PortfolioCreateRequest>(
      '/api/portfolios',
      { ...options, method: 'POST', body: request }
    );
  },

  list(options: ApiCallOptions = {}): Promise<PortfolioListResponse> {
    return apiRequest<PortfolioListResponse>('/api/portfolios', options);
  },

  get(
    portfolioId: Uuid,
    options: ApiCallOptions = {}
  ): Promise<PortfolioResponse> {
    return apiRequest<PortfolioResponse>(portfolioPath(portfolioId), options);
  },

  update(
    portfolioId: Uuid,
    request: PortfolioUpdateRequest,
    options: ApiCallOptions = {}
  ): Promise<PortfolioResponse> {
    return apiRequest<PortfolioResponse, PortfolioUpdateRequest>(
      portfolioPath(portfolioId),
      { ...options, method: 'PATCH', body: request }
    );
  },

  replaceHoldings(
    portfolioId: Uuid,
    request: PortfolioHoldingsReplaceRequest,
    options: ApiCallOptions = {}
  ): Promise<PortfolioResponse> {
    return apiRequest<PortfolioResponse, PortfolioHoldingsReplaceRequest>(
      `${portfolioPath(portfolioId)}/holdings`,
      { ...options, method: 'PUT', body: request }
    );
  },

  duplicate(
    portfolioId: Uuid,
    request: PortfolioDuplicateRequest,
    options: ApiCallOptions = {}
  ): Promise<PortfolioResponse> {
    return apiRequest<PortfolioResponse, PortfolioDuplicateRequest>(
      `${portfolioPath(portfolioId)}/duplicate`,
      { ...options, method: 'POST', body: request }
    );
  },

  delete(portfolioId: Uuid, options: ApiCallOptions = {}): Promise<void> {
    return apiRequest<void>(portfolioPath(portfolioId), {
      ...options,
      method: 'DELETE',
      responseMode: 'none'
    });
  }
};
