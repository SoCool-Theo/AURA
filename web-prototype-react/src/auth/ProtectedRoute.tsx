import { useEffect } from 'react';
import type { ReactNode } from 'react';
import { go } from '../app/routes';
import { useAuth } from './useAuth';
import styles from './ProtectedRoute.module.css';

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const {
    logout,
    retrySessionRestore,
    sessionError,
    status,
  } = useAuth();

  useEffect(() => {
    if (status === 'unauthenticated') go('login');
  }, [status]);

  if (status === 'initializing') {
    return (
      <main className={styles.boundary} aria-busy="true">
        <p role="status">Restoring your Aura session…</p>
      </main>
    );
  }

  if (status === 'error') {
    return (
      <main className={styles.boundary}>
        <section role="alert">
          <h1>Session verification unavailable</h1>
          <p>{sessionError}</p>
          <div>
            <button type="button" onClick={() => void retrySessionRestore()}>
              Try again
            </button>
            <button
              type="button"
              onClick={() => {
                logout();
                go('login');
              }}
            >
              Return to sign in
            </button>
          </div>
        </section>
      </main>
    );
  }

  if (status !== 'authenticated') return null;
  return children;
}
