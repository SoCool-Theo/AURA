import { ApiError } from '../../api/apiClient';

export function portfolioErrorMessage(
  error: unknown,
  fallback: string,
): string {
  return error instanceof ApiError ? error.message : fallback;
}

export function formatPortfolioDate(value: string): string {
  return new Date(value).toLocaleString();
}
