import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import type { ReactNode } from 'react';
import { getCurrentUser, loginUser, logoutWebSession, refreshWebSession, registerUser } from '../api/authApi';
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
  setCurrentUser: (user: AuthenticatedUserResponse) => void;
  logout: () => Promise<void>;
  retrySessionRestore: () => Promise<void>;
};

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function isAuthenticationFailure(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}

function webSessionIdentity(token: string): { sub: string; sid: string } | null {
  // These tokens come from the API; parsing here only guards UI identity.
  // Signature validation and authorization remain exclusively in the backend.
  try {
    const payload = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    const claims = JSON.parse(atob(payload.padEnd(Math.ceil(payload.length / 4) * 4, '=')));
    return typeof claims.sub === 'string' && claims.sub
      && typeof claims.sid === 'string' && claims.sid ? claims : null;
  } catch { return null; }
}

function sameWebSession(previous: string, next: string): boolean {
  const a = webSessionIdentity(previous), b = webSessionIdentity(next);
  return Boolean(a && b && a.sub === b.sub && a.sid === b.sid);
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
  const sessionVersion = useRef(0);
  const pendingRefresh = useRef<Promise<string | null> | null>(null);
  const replacedAccessToken = useRef<string | null>(null);

  const invalidateSession = useCallback((rejectedToken?: string) => {
    if (rejectedToken && readAccessToken() !== rejectedToken) return;
    sessionVersion.current += 1;
    replacedAccessToken.current = null;

    try {
      clearAccessToken();
    } finally {
      // A removed account must leave authenticated UI even if storage fails.
      setUser(null);
      setSessionError(null);
      setStatus('unauthenticated');
    }
  }, []);

  const refreshAccessToken = useCallback((rejectedToken?: string): Promise<string | null> => {
    const currentToken = readAccessToken();
    if (rejectedToken && currentToken !== rejectedToken) {
      return Promise.resolve(replacedAccessToken.current === rejectedToken ? currentToken : null);
    }
    if (pendingRefresh.current) {
      return pendingRefresh.current.then(token => {
        if (token && rejectedToken && !sameWebSession(rejectedToken, token)) {
          throw new ApiError({ kind: 'http', status: 401,
            message: 'Your sign-in session changed. Please sign in again.' });
        }
        return token;
      });
    }

    const version = sessionVersion.current;
    const renewal = refreshWebSession().then(response => {
      // A late response must never restore a signed-out or replaced account.
      if (sessionVersion.current !== version) return null;
      if (rejectedToken && !sameWebSession(rejectedToken, response.access_token)) {
        throw new ApiError({ kind: 'http', status: 401,
          message: 'Your sign-in session changed. Please sign in again.' });
      }
      replacedAccessToken.current = currentToken;
      storeAccessToken(response.access_token);
      return response.access_token;
    }).finally(() => {
      if (pendingRefresh.current === renewal) pendingRefresh.current = null;
    });
    pendingRefresh.current = renewal;
    return renewal;
  }, []);

  const restoreSession = useCallback(async () => {
    const version = sessionVersion.current;
    setStatus('initializing');
    setSessionError(null);

    try {
      const token = await refreshAccessToken();
      if (!token || sessionVersion.current !== version) return;
      const currentUser = await getCurrentUser();
      if (sessionVersion.current !== version) return;

      setUser(currentUser);
      setStatus('authenticated');
    } catch (error) {
      if (sessionVersion.current !== version) return;

      setUser(null);
      if (isAuthenticationFailure(error)) {
        invalidateSession();
        return;
      }

      setSessionError(sessionRestoreMessage(error));
      setStatus('error');
    }
  }, [invalidateSession, refreshAccessToken]);

  useEffect(() => configureApiAuthentication({
    getAccessToken: readAccessToken,
    onUnauthorized: invalidateSession,
    refreshAccessToken,
  }), [invalidateSession, refreshAccessToken]);

  useEffect(() => {
    if (restorationStarted.current) return;
    restorationStarted.current = true;
    void restoreSession();
  }, [restoreSession]);

  const login = useCallback(async (request: LoginRequest) => {
    const version = ++sessionVersion.current;
    replacedAccessToken.current = null;
    const tokenResponse = await loginUser(request);
    if (sessionVersion.current !== version) return;
    storeAccessToken(tokenResponse.access_token);
    setStatus('initializing');
    setSessionError(null);

    try {
      const currentUser = await getCurrentUser({
        token: tokenResponse.access_token,
      });
      if (sessionVersion.current !== version) return;

      setUser(currentUser);
      setStatus('authenticated');
    } catch (error) {
      if (sessionVersion.current !== version) return;
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

  const logout = useCallback(async () => {
    const version = ++sessionVersion.current;
    // Keep failures visible to the caller. A failed server logout must not
    // appear successful while leaving a restorable browser cookie behind.
    await logoutWebSession(webSessionIdentity(readAccessToken() ?? '')?.sid);
    if (sessionVersion.current === version) invalidateSession();
  }, [invalidateSession]);

  const value = useMemo<AuthContextValue>(() => ({
    user,
    status,
    sessionError,
    login,
    register,
    setCurrentUser: setUser,
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
