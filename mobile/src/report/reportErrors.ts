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
  const messages = validationMessages(error);
  return messages.length ? messages.join('. ') : error.message;
}
