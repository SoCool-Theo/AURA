import { ApiError } from '../api/apiClient';

function validationMessages(error: ApiError): string[] {
  if (!Array.isArray(error.detail)) return [];

  return error.detail.flatMap((item) => {
    if (
      item !== null
      && typeof item === 'object'
      && !Array.isArray(item)
      && typeof item.msg === 'string'
      && item.msg.trim()
    ) {
      return [item.msg];
    }
    return [];
  });
}

export function reportErrorMessage(
  error: unknown,
  fallback = 'Aura could not complete the report request.'
): string {
  if (!(error instanceof ApiError)) return fallback;
  if (error.status === 409) {
    return 'This portfolio cannot be analyzed until its holdings use one complete supported format.';
  }
  if (error.status === 503) {
    return 'Required current market or currency data is unavailable or stale. No report was saved.';
  }
  const messages = validationMessages(error);
  return messages.length ? messages.join('. ') : error.message;
}
