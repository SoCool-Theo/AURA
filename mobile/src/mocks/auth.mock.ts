import type { DemoAuraUser, DemoAuthResult } from '../types/demo';

function mockUser(email: string, name = 'Aura Investor'): DemoAuraUser {
  return {
    id: 'mock-user-1',
    email,
    name
  };
}

export const demoAuthApi = {
  async login(email: string, password: string): Promise<DemoAuthResult> {
    if (!email || !password) {
      throw new Error('Email and password are required.');
    }
    return { accessToken: 'mock-aura-token', user: mockUser(email) };
  },

  async register(
    name: string,
    email: string,
    password: string
  ): Promise<DemoAuthResult> {
    if (!name || !email || !password) {
      throw new Error('Name, email, and password are required.');
    }
    return { accessToken: 'mock-aura-token', user: mockUser(email, name) };
  },

  async me(): Promise<DemoAuraUser> {
    return mockUser('demo@aura.app');
  }
};
