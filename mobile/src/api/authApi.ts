import { environment } from '../config/environment';
import type { AuraUser, AuthResult } from '../types/auth';
import { apiClient } from './apiClient';

const mockUser = (email: string, name = 'Aura Investor'): AuraUser => ({
  id: 'mock-user-1',
  email,
  name
});

export const authApi = {
  async login(email: string, password: string): Promise<AuthResult> {
    if (environment.useMocks) {
      if (!email || !password) throw new Error('Email and password are required.');
      return { accessToken: 'mock-aura-token', user: mockUser(email) };
    }
    const token = await apiClient<{ access_token: string }>('/api/auth/login', {
      method: 'POST',
      authenticated: false,
      body: JSON.stringify({ email, password })
    });
    const user = await apiClient<AuraUser>('/api/auth/me', {
      headers: { Authorization: `Bearer ${token.access_token}` }
    });
    return { accessToken: token.access_token, user };
  },

  async register(name: string, email: string, password: string): Promise<AuthResult> {
    if (environment.useMocks) {
      return { accessToken: 'mock-aura-token', user: mockUser(email, name) };
    }
    await apiClient('/api/auth/register', {
      method: 'POST',
      authenticated: false,
      body: JSON.stringify({ email, password })
    });
    return this.login(email, password);
  },

  async me(token: string): Promise<AuraUser> {
    if (environment.useMocks) return mockUser('demo@aura.app');
    return apiClient<AuraUser>('/api/auth/me', {
      headers: { Authorization: `Bearer ${token}` }
    });
  }
};
