import { ApiError } from '../../api/apiClient';

export function portfolioErrorMessage(
  error: unknown,
  fallback: string,
): string {
  return error instanceof ApiError ? error.message : fallback;
}

export function displayPercentage(decimalWeight: number): string {
  return Number((decimalWeight * 100).toFixed(10)).toString();
}

export function requestWeight(displayedPercentage: string): number {
  return Number(displayedPercentage) / 100;
}

export function formatPortfolioDate(value: string): string {
  return new Date(value).toLocaleString();
}
