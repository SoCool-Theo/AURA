import type { ApiCallOptions } from '../types/api';
import type {
  AccessTokenResponse,
  AuthenticatedUserResponse,
  LoginRequest,
  PasswordChangeRequest,
  ProfileUpdateRequest,
  RegistrationRequest,
} from '../types/auth';
import { apiRequest } from './apiClient';

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
  return apiRequest<AccessTokenResponse, LoginRequest>('/api/auth/login', {
    method: 'POST',
    body: request,
    signal,
    token: null,
  });
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
