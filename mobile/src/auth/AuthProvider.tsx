import React, {
  createContext,
  PropsWithChildren,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from 'react';
import { authApi } from '../api/authApi';
import { ApiError, configureApiAuthentication } from '../api/apiClient';
import type {
  AuthenticatedUserResponse,
  LoginRequest,
  RegistrationRequest
} from '../types/auth';
import { clearToken, getToken, saveToken } from './authStorage';
import { sessionRestoreErrorMessage } from './authErrors';

export type AuthStatus =
  | 'initializing'
  | 'authenticated'
  | 'unauthenticated'
  | 'error';

type AuthContextValue = {
  user: AuthenticatedUserResponse | null;
  status: AuthStatus;
  sessionError: string | null;
  signIn: (request: LoginRequest) => Promise<void>;
  register: (
    request: RegistrationRequest
  ) => Promise<AuthenticatedUserResponse>;
  signOut: () => Promise<void>;
  retrySessionRestore: () => Promise<void>;
};

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<AuthenticatedUserResponse | null>(null);
  const [status, setStatus] = useState<AuthStatus>('initializing');
  const [sessionError, setSessionError] = useState<string | null>(null);
  const activeTokenRef = useRef<string | null>(null);
  const invalidationRef = useRef<Promise<void> | null>(null);
  const restorationAttemptRef = useRef(0);

  const invalidateSession = useCallback(async (
    rejectedToken?: string | null
  ): Promise<void> => {
    if (rejectedToken === null) return;
    if (
      rejectedToken !== undefined
      && activeTokenRef.current !== rejectedToken
    ) {
      return;
    }
    if (invalidationRef.current) return invalidationRef.current;

    restorationAttemptRef.current += 1;
    activeTokenRef.current = null;
    const invalidation = (async () => {
      try {
        await clearToken();
        setUser(null);
        setSessionError(null);
        setStatus('unauthenticated');
      } catch (error) {
        setUser(null);
        setSessionError('Aura could not remove the saved session from this device. Retry sign out.');
        setStatus('error');
        throw error;
      }
    })();
    invalidationRef.current = invalidation;

    try {
      await invalidation;
    } finally {
      if (invalidationRef.current === invalidation) {
        invalidationRef.current = null;
      }
    }
  }, []);

  const restoreSession = useCallback(async (): Promise<void> => {
    const attempt = restorationAttemptRef.current + 1;
    restorationAttemptRef.current = attempt;
    setStatus('initializing');
    setSessionError(null);

    let token: string | null;
    try {
      token = await getToken();
    } catch (error) {
      if (restorationAttemptRef.current !== attempt) return;
      activeTokenRef.current = null;
      setUser(null);
      setSessionError(sessionRestoreErrorMessage(error));
      setStatus('error');
      return;
    }

    if (restorationAttemptRef.current !== attempt) return;
    activeTokenRef.current = token;
    if (!token) {
      setUser(null);
      setStatus('unauthenticated');
      return;
    }

    try {
      const currentUser = await authApi.me({ token });
      if (
        restorationAttemptRef.current !== attempt
        || activeTokenRef.current !== token
      ) {
        return;
      }
      setUser(currentUser);
      setStatus('authenticated');
    } catch (error) {
      if (
        restorationAttemptRef.current !== attempt
        || activeTokenRef.current !== token
      ) {
        return;
      }

      setUser(null);
      if (error instanceof ApiError && error.status === 401) {
        await invalidateSession(token);
        return;
      }

      setSessionError(sessionRestoreErrorMessage(error));
      setStatus('error');
    }
  }, [invalidateSession]);

  useEffect(() => {
    return configureApiAuthentication({
      getAccessToken: getToken,
      onAuthenticationRejected: invalidateSession
    });
  }, [invalidateSession]);

  useEffect(() => {
    void restoreSession();
  }, [restoreSession]);

  const signIn = useCallback(async (request: LoginRequest): Promise<void> => {
    const tokenResponse = await authApi.login(request);
    const accessToken = tokenResponse.access_token.trim();
    await saveToken(accessToken);
    activeTokenRef.current = accessToken;
    const attempt = restorationAttemptRef.current + 1;
    restorationAttemptRef.current = attempt;
    setUser(null);
    setSessionError(null);
    setStatus('initializing');

    try {
      const currentUser = await authApi.me({ token: accessToken });
      if (
        restorationAttemptRef.current !== attempt
        || activeTokenRef.current !== accessToken
      ) {
        return;
      }
      setUser(currentUser);
      setStatus('authenticated');
    } catch (error) {
      if (
        restorationAttemptRef.current === attempt
        && activeTokenRef.current === accessToken
      ) {
        setUser(null);
        if (error instanceof ApiError && error.status === 401) {
          await invalidateSession(activeTokenRef.current);
        } else {
          setSessionError(sessionRestoreErrorMessage(error));
          setStatus('error');
        }
      }
      throw error;
    }
  }, [invalidateSession]);

  const register = useCallback((request: RegistrationRequest) => (
    authApi.register(request)
  ), []);

  const signOut = useCallback(() => invalidateSession(), [invalidateSession]);

  const value = useMemo<AuthContextValue>(() => ({
    user,
    status,
    sessionError,
    signIn,
    register,
    signOut,
    retrySessionRestore: restoreSession
  }), [
    register,
    restoreSession,
    sessionError,
    signIn,
    signOut,
    status,
    user
  ]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
