import type { ApiCallOptions } from '../types/api';
import type {
  AccessTokenResponse,
  AuthenticatedUserResponse,
  LoginRequest,
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
