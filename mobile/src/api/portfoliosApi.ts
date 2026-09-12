import type { ApiCallOptions, Uuid } from '../types/api';
import type {
  PortfolioCreateRequest,
  PortfolioCurrency,
  PortfolioDuplicateRequest,
  PortfolioHoldingsReplaceRequest,
  PortfolioListResponse,
  PortfolioRealHoldingInput,
  PortfolioResponse,
  PortfolioUpdateRequest,
  PortfolioValuationResponse
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

  getValuation(
    portfolioId: Uuid,
    currency: PortfolioCurrency = 'USD',
    options: ApiCallOptions = {}
  ): Promise<PortfolioValuationResponse> {
    return apiRequest<PortfolioValuationResponse>(
      `${portfolioPath(portfolioId)}/valuation?currency=${currency}`,
      options
    );
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

  replaceRealHoldings(
    portfolioId: Uuid,
    holdings: PortfolioRealHoldingInput[],
    options: ApiCallOptions = {}
  ): Promise<PortfolioResponse> {
    return apiRequest<PortfolioResponse, PortfolioHoldingsReplaceRequest>(
      `${portfolioPath(portfolioId)}/holdings`,
      { ...options, method: 'PUT', body: { holdings } }
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
