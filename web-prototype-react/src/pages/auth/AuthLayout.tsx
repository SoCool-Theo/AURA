import type { ReactNode } from 'react';
import styles from './AuthPage.module.css';

interface AuthLayoutProps {
  children: ReactNode;
}

export function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <main className={styles.authShell}>
      <a className={styles.welcomeLink} href="#/welcome">← Back to Aura</a>
      <div className={styles.authBackdrop} aria-hidden="true" />
      <section className={styles.authCard} aria-label="Aura account access">
        <header className={styles.authBrand}>
          <div className={styles.brandRow}>
            <span className={styles.brandMark} aria-hidden="true" />
            <span className={styles.brandName}>AURA</span>
          </div>
          <p>Portfolio Risk Intelligence</p>
        </header>
        {children}
      </section>
    </main>
  );
}
