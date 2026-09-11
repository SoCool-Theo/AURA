import type { ApiCallOptions } from '../types/api';
import type {
  AccessTokenResponse,
  AuthenticatedUserResponse,
  LoginRequest,
  RegistrationRequest
} from '../types/auth';
import { apiRequest } from './apiClient';

export const authApi = {
  register(
    request: RegistrationRequest,
    options: ApiCallOptions = {}
  ): Promise<AuthenticatedUserResponse> {
    return apiRequest<AuthenticatedUserResponse, RegistrationRequest>(
      '/api/auth/register',
      { ...options, method: 'POST', body: request, token: null }
    );
  },

  login(
    request: LoginRequest,
    options: ApiCallOptions = {}
  ): Promise<AccessTokenResponse> {
    return apiRequest<AccessTokenResponse, LoginRequest>('/api/auth/login', {
      ...options,
      method: 'POST',
      body: request,
      token: null
    });
  },

  me(options: ApiCallOptions = {}): Promise<AuthenticatedUserResponse> {
    return apiRequest<AuthenticatedUserResponse>('/api/auth/me', options);
  }
};
