import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import type { ReactNode } from 'react';
import { getCurrentUser, loginUser, registerUser } from '../api/authApi';
import { ApiError, configureApiAuthentication } from '../api/apiClient';
import type {
  AuthenticatedUserResponse,
  LoginRequest,
  RegistrationRequest,
} from '../types/auth';
import {
  clearAccessToken,
  readAccessToken,
  storeAccessToken,
} from './authStorage';

export type AuthStatus =
  | 'initializing'
  | 'authenticated'
  | 'unauthenticated'
  | 'error';

export type AuthContextValue = {
  user: AuthenticatedUserResponse | null;
  status: AuthStatus;
  sessionError: string | null;
  login: (request: LoginRequest) => Promise<void>;
  register: (
    request: RegistrationRequest,
  ) => Promise<AuthenticatedUserResponse>;
  logout: () => void;
  retrySessionRestore: () => Promise<void>;
};

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function isAuthenticationFailure(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}

function sessionRestoreMessage(error: unknown): string {
  if (error instanceof ApiError && error.kind === 'configuration') {
    return error.message;
  }
  return 'Aura could not verify your session. Check the service connection and try again.';
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthenticatedUserResponse | null>(null);
  const [status, setStatus] = useState<AuthStatus>('initializing');
  const [sessionError, setSessionError] = useState<string | null>(null);
  const restorationStarted = useRef(false);

  const invalidateSession = useCallback((rejectedToken?: string) => {
    if (rejectedToken && readAccessToken() !== rejectedToken) return;

    clearAccessToken();
    setUser(null);
    setSessionError(null);
    setStatus('unauthenticated');
  }, []);

  const restoreSession = useCallback(async () => {
    const token = readAccessToken();
    if (!token) {
      setUser(null);
      setSessionError(null);
      setStatus('unauthenticated');
      return;
    }

    setStatus('initializing');
    setSessionError(null);

    try {
      const currentUser = await getCurrentUser({ token });
      if (readAccessToken() !== token) return;

      setUser(currentUser);
      setStatus('authenticated');
    } catch (error) {
      if (readAccessToken() !== token) return;

      setUser(null);
      if (isAuthenticationFailure(error)) {
        invalidateSession(token);
        return;
      }

      setSessionError(sessionRestoreMessage(error));
      setStatus('error');
    }
  }, [invalidateSession]);

  useEffect(() => configureApiAuthentication({
    getAccessToken: readAccessToken,
    onUnauthorized: invalidateSession,
  }), [invalidateSession]);

  useEffect(() => {
    if (restorationStarted.current) return;
    restorationStarted.current = true;
    void restoreSession();
  }, [restoreSession]);

  const login = useCallback(async (request: LoginRequest) => {
    const tokenResponse = await loginUser(request);
    storeAccessToken(tokenResponse.access_token);
    setStatus('initializing');
    setSessionError(null);

    try {
      const currentUser = await getCurrentUser({
        token: tokenResponse.access_token,
      });
      if (readAccessToken() !== tokenResponse.access_token) return;

      setUser(currentUser);
      setStatus('authenticated');
    } catch (error) {
      if (isAuthenticationFailure(error)) {
        invalidateSession(tokenResponse.access_token);
      } else {
        setUser(null);
        setSessionError(sessionRestoreMessage(error));
        setStatus('error');
      }
      throw error;
    }
  }, [invalidateSession]);

  const register = useCallback((request: RegistrationRequest) => (
    registerUser(request)
  ), []);

  const logout = useCallback(() => {
    invalidateSession();
  }, [invalidateSession]);

  const value = useMemo<AuthContextValue>(() => ({
    user,
    status,
    sessionError,
    login,
    register,
    logout,
    retrySessionRestore: restoreSession,
  }), [
    login,
    logout,
    register,
    restoreSession,
    sessionError,
    status,
    user,
  ]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
