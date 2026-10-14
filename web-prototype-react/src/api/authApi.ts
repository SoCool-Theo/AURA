import type { ApiCallOptions } from '../types/api';
import type {
  AccessTokenResponse,
  AccountDeletionRequest,
  AuthenticatedUserResponse,
  LoginRequest,
  PasswordChangeRequest,
  ProfileUpdateRequest,
  RegistrationRequest,
} from '../types/auth';
import { ApiError, apiRequest } from './apiClient';
import { withWebSessionLock } from '../auth/webSessionLock';

const webSessionOptions = {
  method: 'POST' as const,
  credentials: 'include' as const,
  headers: { 'X-Aura-Web-Session': '1' },
  token: null,
};

export function registerUser(
  request: RegistrationRequest,
  signal?: AbortSignal,
): Promise<AuthenticatedUserResponse> {
  return apiRequest<AuthenticatedUserResponse, RegistrationRequest>(
    '/api/auth/register',
    { method: 'POST', body: request, signal, token: null },
  );
}

export function loginUser(
  request: LoginRequest,
  signal?: AbortSignal,
): Promise<AccessTokenResponse> {
  return withWebSessionLock(() => apiRequest<AccessTokenResponse, LoginRequest>('/api/auth/web/login', {
    ...webSessionOptions,
    body: request,
    signal,
  }));
}

export function refreshWebSession(): Promise<AccessTokenResponse> {
  return withWebSessionLock(async () => {
    try {
      return await apiRequest<AccessTokenResponse>('/api/auth/web/refresh', webSessionOptions);
    } catch (error) {
      // An overlapping tab may have updated the shared cookie. Retry once;
      // a conflict never grants tokens for a previously used refresh secret.
      if (!(error instanceof ApiError) || error.status !== 409) throw error;
      return apiRequest<AccessTokenResponse>('/api/auth/web/refresh', webSessionOptions);
    }
  });
}

export function logoutWebSession(expectedSessionId?: string): Promise<void> {
  return withWebSessionLock(() => apiRequest<void>('/api/auth/web/logout', {
    ...webSessionOptions,
    headers: { ...webSessionOptions.headers,
      ...(expectedSessionId ? { 'X-Aura-Web-Session-Id': expectedSessionId } : {}),
    },
  }));
}

export function getCurrentUser(
  options: ApiCallOptions = {},
): Promise<AuthenticatedUserResponse> {
  return apiRequest<AuthenticatedUserResponse>('/api/auth/me', options);
}

export function updateCurrentUserProfile(
  request: ProfileUpdateRequest,
  options: ApiCallOptions = {},
): Promise<AuthenticatedUserResponse> {
  return apiRequest<AuthenticatedUserResponse, ProfileUpdateRequest>(
    '/api/auth/me',
    { ...options, method: 'PATCH', body: request },
  );
}

export function changeCurrentUserPassword(
  request: PasswordChangeRequest,
  options: ApiCallOptions = {},
): Promise<void> {
  return apiRequest<void, PasswordChangeRequest>('/api/auth/me/password', {
    ...options,
    method: 'PUT',
    body: request,
  });
}

export function deleteCurrentUserAccount(
  request: AccountDeletionRequest,
  options: ApiCallOptions = {},
): Promise<void> {
  return apiRequest<void, AccountDeletionRequest>('/api/auth/me', {
    ...options, method: 'DELETE', body: request,
  });
}
