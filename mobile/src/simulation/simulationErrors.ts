import { ApiError } from '../api/apiClient';

function validationMessages(error: ApiError): string[] {
  if (!Array.isArray(error.detail)) return [];
  return error.detail.flatMap((item) => (
    item !== null
    && typeof item === 'object'
    && !Array.isArray(item)
    && typeof item.msg === 'string'
    && item.msg.trim()
      ? [item.msg]
      : []
  ));
}

export function simulationErrorMessage(
  error: unknown,
  fallback = 'Aura could not complete the simulation request.'
): string {
  if (!(error instanceof ApiError)) return fallback;
  if (error.status === 409) {
    return 'This portfolio cannot be simulated until its holdings use one complete supported format.';
  }
  if (error.status === 503) {
    return 'Required current market data is unavailable or stale. No simulation snapshot was saved.';
  }
  const messages = validationMessages(error);
  return messages.length ? messages.join('. ') : error.message;
}
