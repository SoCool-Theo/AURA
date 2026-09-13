import { ApiError } from '../api/apiClient';

export function agentErrorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return 'Aura could not prepare an explanation. Please try again.';
  }

  switch (error.status) {
    case 401:
      return 'Your session has ended. Please sign in again.';
    case 404:
      return 'The selected portfolio or its requested context could not be found.';
    case 422:
      return 'Aura could not process that question. Check the selected portfolio and try again.';
    case 502:
      return 'Aura received an invalid AI explanation. Please try again.';
    case 503:
      return 'Aura\u2019s AI service is temporarily unavailable. Please try again later.';
  }

  switch (error.kind) {
    case 'configuration':
      return 'Aura is not configured to connect to its service.';
    case 'network':
      return 'Unable to reach Aura. Check your connection and try again.';
    case 'malformed-response':
      return 'Aura returned an unexpected AI response. Please try again.';
    default:
      return 'Aura could not prepare an explanation. Please try again.';
  }
}
