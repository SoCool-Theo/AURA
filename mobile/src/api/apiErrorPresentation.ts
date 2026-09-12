import { ApiError } from './apiClient';

export type ApiErrorCode =
  | '401'
  | '404'
  | '409'
  | '422'
  | '500'
  | '503'
  | 'NETWORK'
  | 'FORM'
  | 'ERROR';

export type ApiErrorPresentation = {
  code: ApiErrorCode;
  title: string;
  message: string;
  icon: 'cloud-offline-outline' | 'lock-closed-outline' | 'search-outline' | 'alert-circle-outline' | 'server-outline';
  retryable: boolean;
};

type PresentationOptions = {
  fallbackMessage?: string;
  resourceName?: string;
  message?: string;
};

export type ApiValidationIssue = {
  path: string;
  message: string;
};

function safeMessage(error: ApiError, fallback: string): string {
  if (error.status !== null && error.status >= 500) return fallback;
  return error.message.trim() || fallback;
}

export function apiValidationIssues(error: unknown): ApiValidationIssue[] {
  if (!(error instanceof ApiError) || error.status !== 422 || !Array.isArray(error.detail)) {
    return [];
  }

  return error.detail.flatMap((item) => {
    if (
      item === null
      || typeof item !== 'object'
      || Array.isArray(item)
      || typeof item.msg !== 'string'
      || !item.msg.trim()
    ) {
      return [];
    }
    const rawLocation = Array.isArray(item.loc) ? item.loc : [];
    const path = rawLocation
      .filter((part) => part !== 'body')
      .map(String)
      .join('.');
    return [{ path, message: item.msg.trim() }];
  });
}

export function apiErrorPresentation(
  error: unknown,
  options: PresentationOptions = {}
): ApiErrorPresentation {
  const fallback = options.fallbackMessage ?? 'Aura could not complete this request.';
  const resource = options.resourceName ?? 'This item';

  if (!(error instanceof ApiError)) {
    return {
      code: 'ERROR',
      title: 'Something went wrong',
      message: options.message ?? fallback,
      icon: 'alert-circle-outline',
      retryable: true
    };
  }

  if (error.kind === 'network') {
    return {
      code: 'NETWORK',
      title: 'Cannot connect to Aura',
      message: options.message ?? 'Check your internet connection, then try again.',
      icon: 'cloud-offline-outline',
      retryable: true
    };
  }

  if (error.status === 401) {
    return {
      code: '401',
      title: 'Session expired',
      message: options.message ?? 'Sign in again to continue securely.',
      icon: 'lock-closed-outline',
      retryable: false
    };
  }

  if (error.status === 404) {
    return {
      code: '404',
      title: `${resource} not found`,
      message: options.message ?? `${resource} may have been deleted or is no longer available.`,
      icon: 'search-outline',
      retryable: false
    };
  }

  if (error.status === 422) {
    const issues = apiValidationIssues(error);
    return {
      code: '422',
      title: 'Check your information',
      message: options.message ?? (issues.length
        ? issues.map((issue) => issue.message).join('. ')
        : safeMessage(error, 'Correct the highlighted information and try again.')),
      icon: 'alert-circle-outline',
      retryable: false
    };
  }

  if (error.status === 409) {
    return {
      code: '409',
      title: 'Portfolio needs attention',
      message: options.message ?? safeMessage(error, fallback),
      icon: 'alert-circle-outline',
      retryable: false
    };
  }

  if (error.status === 503) {
    return {
      code: '503',
      title: 'Data temporarily unavailable',
      message: options.message ?? fallback,
      icon: 'server-outline',
      retryable: true
    };
  }

  if (error.status !== null && error.status >= 500) {
    return {
      code: '500',
      title: 'Aura ran into a problem',
      message: options.message ?? 'The server could not complete the request. Please try again.',
      icon: 'server-outline',
      retryable: true
    };
  }

  return {
    code: 'ERROR',
    title: 'Request unsuccessful',
    message: options.message ?? safeMessage(error, fallback),
    icon: 'alert-circle-outline',
    retryable: true
  };
}
