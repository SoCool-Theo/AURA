import { ApiError } from '../api/apiClient';
import type { PortfolioResponse } from '../types/portfolio';

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
