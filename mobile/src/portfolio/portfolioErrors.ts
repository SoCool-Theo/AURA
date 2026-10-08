import { ApiError } from '../api/apiClient';
import type { PortfolioResponse } from '../types/portfolio';

export const PORTFOLIO_MARKET_DATA_RECOVERY_MESSAGE =
  'New analysis is unavailable until market data is refreshed. Retry the current value after the refresh completes.';

function validationMessage(error: ApiError): string | null {
  if (!Array.isArray(error.detail)) return null;

  for (const item of error.detail) {
    if (
      item !== null
      && typeof item === 'object'
      && !Array.isArray(item)
      && typeof item.msg === 'string'
      && item.msg.trim()
    ) {
      return item.msg;
    }
  }
  return null;
}

export function portfolioErrorMessage(
  error: unknown,
  fallback = 'Aura could not complete the portfolio request.'
): string {
  if (!(error instanceof ApiError)) return fallback;
  return validationMessage(error) ?? error.message;
}

export function portfolioValuationErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 409) {
    return 'This portfolio cannot be valued until all holdings use one complete real-holding format.';
  }
  if (error instanceof ApiError && error.status === 503) {
    return 'Current valuation is temporarily unavailable because required market or currency data is missing or stale.';
  }
  return portfolioErrorMessage(error, 'Current valuation is unavailable.');
}

export function isPortfolioMarketDataUnavailable(error: unknown): boolean {
  return error instanceof ApiError && error.status === 503;
}

export class PortfolioCreatedWithoutHoldingsError extends Error {
  readonly portfolio: PortfolioResponse;
  readonly causeValue: unknown;

  constructor(portfolio: PortfolioResponse, cause: unknown) {
    super('The portfolio was created, but its holdings could not be saved.');
    this.name = 'PortfolioCreatedWithoutHoldingsError';
    this.portfolio = portfolio;
    this.causeValue = cause;
  }
}
