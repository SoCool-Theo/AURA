import { ApiError } from './apiClient';

export type ApiErrorCode =
  | '401'
  | '404'
  | '409'
  | '422'
  | '500'
  | '503'
  | 'NETWORK'
  | 'CONFIG'
  | 'FORM'
  | 'ERROR';

export type ApiErrorPresentation = {
  code: ApiErrorCode;
  title: string;
  message: string;
  icon: 'offline' | 'lock' | 'search' | 'alert' | 'server';
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
  return error.detail.flatMap(item => {
    const issue = item as Record<string, unknown>;
    if (
      item === null
      || typeof item !== 'object'
      || Array.isArray(item)
      || typeof issue.msg !== 'string'
      || !issue.msg.trim()
    ) {
      return [];
    }
    const rawLocation = Array.isArray(issue.loc) ? issue.loc : [];
    const path = rawLocation.filter(part => part !== 'body').map(String).join('.');
    return [{ path, message: issue.msg.trim() }];
  });
}

export function apiErrorPresentation(
  error: unknown,
  options: PresentationOptions = {},
): ApiErrorPresentation {
  const fallback = options.fallbackMessage ?? 'Aura could not complete this request.';
  const resource = options.resourceName ?? 'This item';

  if (typeof error === 'string') {
    if (options.resourceName && /not found/i.test(error)) {
      return { code: '404', title: resource + ' not found', message: options.message ?? resource + ' may have been deleted or is no longer available.', icon: 'search', retryable: false };
    }
    return { code: 'FORM', title: 'Check your information', message: options.message ?? error, icon: 'alert', retryable: false };
  }
  if (!(error instanceof ApiError)) {
    return { code: 'ERROR', title: 'Something went wrong', message: options.message ?? fallback, icon: 'alert', retryable: true };
  }
  if (error.kind === 'network') {
    return { code: 'NETWORK', title: 'Cannot connect to Aura', message: options.message ?? 'Check your connection and make sure the Aura service is reachable, then try again.', icon: 'offline', retryable: true };
  }
  if (error.kind === 'configuration') {
    return { code: 'CONFIG', title: 'Aura is not configured', message: options.message ?? 'The application service connection is not configured.', icon: 'server', retryable: false };
  }
  if (error.status === 401) {
    return { code: '401', title: 'Session expired', message: options.message ?? 'Sign in again to continue securely.', icon: 'lock', retryable: false };
  }
  if (error.status === 404) {
    return { code: '404', title: resource + ' not found', message: options.message ?? resource + ' may have been deleted or is no longer available.', icon: 'search', retryable: false };
  }
  if (error.status === 422) {
    const issues = apiValidationIssues(error);
    return {
      code: '422',
      title: 'Check your information',
      message: options.message ?? (issues.length ? issues.map(issue => issue.message).join('. ') : safeMessage(error, 'Review the information and try again.')),
      icon: 'alert',
      retryable: false,
    };
  }
  if (error.status === 409) {
    return { code: '409', title: 'Portfolio needs attention', message: options.message ?? safeMessage(error, fallback), icon: 'alert', retryable: false };
  }
  if (error.status === 503) {
    return { code: '503', title: 'Data temporarily unavailable', message: options.message ?? fallback, icon: 'server', retryable: true };
  }
  if (error.status !== null && error.status >= 500) {
    return { code: '500', title: 'Aura ran into a problem', message: options.message ?? 'Aura could not complete the request. Please try again.', icon: 'server', retryable: true };
  }
  return { code: 'ERROR', title: 'Request unsuccessful', message: options.message ?? safeMessage(error, fallback), icon: 'alert', retryable: true };
}
