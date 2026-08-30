import React, { createContext, PropsWithChildren, useEffect, useMemo, useState } from 'react';
import type { AuraUser } from '../types/auth';
import { authApi } from '../api/authApi';
import { clearToken, getToken, saveToken } from './authStorage';

type AuthContextValue = {
  user: AuraUser | null;
  isLoading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
};

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<AuraUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const token = await getToken();
      if (token) {
        try {
          setUser(await authApi.me(token));
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
      const result = await authApi.login(email, password);
      await saveToken(result.accessToken);
      setUser(result.user);
    },
    register: async (name, email, password) => {
      const result = await authApi.register(name, email, password);
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
