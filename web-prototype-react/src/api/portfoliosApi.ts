import type { ApiCallOptions, Uuid } from '../types/api';
import type {
  PortfolioCreateRequest,
  PortfolioCurrency,
  PortfolioDuplicateRequest,
  PortfolioHoldingsReplaceRequest,
  PortfolioLegacyHoldingsReplaceRequest,
  PortfolioListResponse,
  PortfolioPlannedAllocationResponse,
  PortfolioPlannedHoldingInput,
  PortfolioPlannedHoldingsReplaceRequest,
  PortfolioPlannedPreviewResponse,
  PortfolioRealHoldingInput,
  PortfolioResponse,
  PortfolioUpdateRequest,
  PortfolioValuationResponse,
} from '../types/portfolio';
import { apiRequest } from './apiClient';

function portfolioPath(portfolioId: Uuid): string {
  return `/api/portfolios/${encodeURIComponent(portfolioId)}`;
}

export function createPortfolio(
  request: PortfolioCreateRequest,
  options: ApiCallOptions = {},
): Promise<PortfolioResponse> {
  return apiRequest<PortfolioResponse, PortfolioCreateRequest>(
    '/api/portfolios',
    { ...options, method: 'POST', body: request },
  );
}

export function listPortfolios(
  options: ApiCallOptions = {},
): Promise<PortfolioListResponse> {
  return apiRequest<PortfolioListResponse>('/api/portfolios', options);
}

export function getPortfolio(
  portfolioId: Uuid,
  options: ApiCallOptions = {},
): Promise<PortfolioResponse> {
  return apiRequest<PortfolioResponse>(portfolioPath(portfolioId), options);
}

export function getPortfolioValuation(
  portfolioId: Uuid,
  currency: PortfolioCurrency = 'USD',
  options: ApiCallOptions = {},
): Promise<PortfolioValuationResponse> {
  return apiRequest<PortfolioValuationResponse>(
    `${portfolioPath(portfolioId)}/valuation?currency=${currency}`,
    options,
  );
}

export function getPlannedPortfolioAllocation(
  portfolioId: Uuid,
  options: ApiCallOptions = {},
): Promise<PortfolioPlannedAllocationResponse> {
  return apiRequest<PortfolioPlannedAllocationResponse>(
    `${portfolioPath(portfolioId)}/planned-allocation`,
    options,
  );
}

export function getPlannedPortfolioPreview(
  portfolioId: Uuid,
  options: ApiCallOptions = {},
): Promise<PortfolioPlannedPreviewResponse> {
  return apiRequest<PortfolioPlannedPreviewResponse>(
    `${portfolioPath(portfolioId)}/planned-preview`,
    options,
  );
}

export function updatePortfolio(
  portfolioId: Uuid,
  request: PortfolioUpdateRequest,
  options: ApiCallOptions = {},
): Promise<PortfolioResponse> {
  return apiRequest<PortfolioResponse, PortfolioUpdateRequest>(
    portfolioPath(portfolioId),
    { ...options, method: 'PATCH', body: request },
  );
}

export function replacePortfolioHoldings(
  portfolioId: Uuid,
  request: PortfolioLegacyHoldingsReplaceRequest,
  options: ApiCallOptions = {},
): Promise<PortfolioResponse> {
  return apiRequest<PortfolioResponse, PortfolioLegacyHoldingsReplaceRequest>(
    `${portfolioPath(portfolioId)}/holdings`,
    { ...options, method: 'PUT', body: request },
  );
}

export function replaceRealPortfolioHoldings(
  portfolioId: Uuid,
  holdings: PortfolioRealHoldingInput[],
  options: ApiCallOptions = {},
): Promise<PortfolioResponse> {
  return apiRequest<PortfolioResponse, PortfolioHoldingsReplaceRequest>(
    `${portfolioPath(portfolioId)}/holdings`,
    { ...options, method: 'PUT', body: { holdings } },
  );
}

export function replacePlannedPortfolioHoldings(
  portfolioId: Uuid,
  holdings: PortfolioPlannedHoldingInput[],
  options: ApiCallOptions = {},
): Promise<PortfolioResponse> {
  return apiRequest<PortfolioResponse, PortfolioPlannedHoldingsReplaceRequest>(
    `${portfolioPath(portfolioId)}/holdings`,
    { ...options, method: 'PUT', body: { holdings } },
  );
}

export function duplicatePortfolio(
  portfolioId: Uuid,
  request: PortfolioDuplicateRequest,
  options: ApiCallOptions = {},
): Promise<PortfolioResponse> {
  return apiRequest<PortfolioResponse, PortfolioDuplicateRequest>(
    `${portfolioPath(portfolioId)}/duplicate`,
    { ...options, method: 'POST', body: request },
  );
}

export function deletePortfolio(
  portfolioId: Uuid,
  options: ApiCallOptions = {},
): Promise<void> {
  return apiRequest<void>(portfolioPath(portfolioId), {
    ...options,
    method: 'DELETE',
  });
}
