import { ApiError } from '../api/apiClient';

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

export function authenticationErrorMessage(
  error: unknown,
  fallback: string
): string {
  if (!(error instanceof ApiError)) return fallback;
  return validationMessage(error) ?? error.message;
}

export function sessionRestoreErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.kind === 'configuration') return error.message;
    if (error.kind === 'network') {
      return 'Aura could not reach the API. Your stored session was kept; check the connection and try again.';
    }
    if (error.kind === 'malformed-response') {
      return 'Aura received an unexpected response while verifying your session. Your stored session was kept.';
    }
    if (error.kind === 'http') {
      return `Aura could not verify your session: ${error.message} Your stored session was kept.`;
    }
  }

  return 'Aura could not verify your session. Your stored session was kept; please try again.';
}
