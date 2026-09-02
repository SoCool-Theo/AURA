import React, { createContext, PropsWithChildren, useEffect, useMemo, useState } from 'react';
import type { DemoAuraUser } from '../types/demo';
import { demoAuthApi } from '../mocks/auth.mock';
import { clearToken, getToken, saveToken } from './authStorage';

type AuthContextValue = {
  user: DemoAuraUser | null;
  isLoading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
};

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<DemoAuraUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const token = await getToken();
      if (token) {
        try {
          setUser(await demoAuthApi.me());
        } catch {
          await clearToken();
        }
      }
      setIsLoading(false);
    })();
  }, []);

  const value = useMemo<AuthContextValue>(() => ({
    user,
    isLoading,
    signIn: async (email, password) => {
      const result = await demoAuthApi.login(email, password);
      await saveToken(result.accessToken);
      setUser(result.user);
    },
    register: async (name, email, password) => {
      const result = await demoAuthApi.register(name, email, password);
      await saveToken(result.accessToken);
      setUser(result.user);
    },
    signOut: async () => {
      await clearToken();
      setUser(null);
    }
  }), [user, isLoading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
