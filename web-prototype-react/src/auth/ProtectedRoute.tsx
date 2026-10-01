import { useEffect } from 'react';
import type { ReactNode } from 'react';
import { go } from '../app/routes';
import { Icon } from '../components/ui/Icon';
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
      <main className={`${styles.boundary} ${styles.loadingBoundary}`} aria-busy="true">
        <header className={styles.loadingHeader}>
          <div className={styles.loadingHeaderInner}>
            <div className={styles.brand} aria-label="Aura">
              <span className={styles.brandMark} aria-hidden="true" />
              <strong>AURA</strong>
            </div>
            <span className={styles.secureSession}>
              <span className={styles.secureIcon}><Icon name="shield" size={18} /></span>
              Secure session
            </span>
          </div>
        </header>

        <section className={styles.loadingStatus} role="status" aria-live="polite" aria-atomic="true">
          <div className={styles.logoWrap} aria-hidden="true">
            <span className={`${styles.orbit} ${styles.outerOrbit}`} />
            <span className={styles.orbit} />
            <span className={styles.loadingMark} />
          </div>
          <h1>Welcome back</h1>
          <p>Restoring your Aura session…</p>
          <span className={styles.loadingDots} aria-hidden="true">
            <i />
            <i />
            <i />
          </span>
        </section>

        <footer className={styles.loadingFooter}>
          Portfolio risk education <span aria-hidden="true">·</span> Not investment advice
        </footer>
      </main>
    );
  }

  if (status === 'error') {
    return (
      <main className={styles.boundary}>
        <section className={styles.errorCard} role="alert">
          <h1>Session verification unavailable</h1>
          <p>{sessionError}</p>
          <div className={styles.errorActions}>
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
