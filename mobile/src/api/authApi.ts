import type { ApiCallOptions } from '../types/api';
import type {
  AccessTokenResponse,
  AccountDeletionRequest,
  AuthenticatedUserResponse,
  LoginRequest,
  PasswordChangeRequest,
  ProfileUpdateRequest,
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
  },

  updateProfile(
    request: ProfileUpdateRequest,
    options: ApiCallOptions = {}
  ): Promise<AuthenticatedUserResponse> {
    return apiRequest<AuthenticatedUserResponse, ProfileUpdateRequest>(
      '/api/auth/me',
      { ...options, method: 'PATCH', body: request }
    );
  },

  deleteAccount(
    request: AccountDeletionRequest,
    options: ApiCallOptions = {}
  ): Promise<void> {
    return apiRequest<void, AccountDeletionRequest>('/api/auth/me', {
      ...options, method: 'DELETE', body: request, responseMode: 'none'
    });
  },

  changePassword(
    request: PasswordChangeRequest,
    options: ApiCallOptions = {}
  ): Promise<void> {
    return apiRequest<void, PasswordChangeRequest>('/api/auth/me/password', {
      ...options,
      method: 'PUT',
      body: request,
      responseMode: 'none'
    });
  }
};
