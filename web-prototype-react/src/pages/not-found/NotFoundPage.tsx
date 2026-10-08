import { go } from '../../app/routes';
import { Icon } from '../../components/ui/Icon';
import styles from './NotFoundPage.module.css';

const SUGGESTED_PAGES = [
  { path: 'portfolios', icon: 'portfolios', title: 'Portfolios', description: 'Manage your portfolios' },
  { path: 'analytics', icon: 'analytics', title: 'Analytics', description: 'Analyze portfolio risk' },
  { path: 'simulations', icon: 'simulations', title: 'Simulations', description: 'Run what-if scenarios' },
  { path: 'assistant', icon: 'assistant', title: 'AI Assistant', description: 'Preview the deferred AI experience' },
  { path: 'reports', icon: 'reports', title: 'Reports', description: 'View your reports' },
] as const;

export function NotFoundPage() {
  function goBack() {
    if (window.history.length > 1) {
      window.history.back();
      return;
    }

    go('dashboard');
  }

  return (
    <div className={styles.notFoundPage}>
      <section className={styles.notFoundHero} aria-labelledby="not-found-title">
        <span className={styles.errorCode} aria-hidden="true">404</span>
        <h1 id="not-found-title">Page Not Found</h1>
        <p>The page you’re looking for doesn’t exist<br />or may have been moved.</p>

        <div className={styles.heroDivider} aria-hidden="true"><span /></div>

        <div className={styles.primaryActions}>
          <button className={styles.dashboardButton} onClick={() => go('dashboard')}>
            <Icon name="dashboard" size={21} />
            Go to Dashboard
          </button>
          <button className={styles.backButton} onClick={goBack}>
            <span aria-hidden="true">←</span>
            Go Back
          </button>
        </div>

        <p className={styles.supportLine}>Support contact options are not available yet.</p>
      </section>

      <section className={styles.suggestions} aria-labelledby="suggested-pages-title">
        <h2 id="suggested-pages-title">You might be looking for</h2>
        <div className={styles.suggestionGrid}>
          {SUGGESTED_PAGES.map(page => (
            <button key={page.path} onClick={() => go(page.path)}>
              <span><Icon name={page.icon} size={25} /></span>
              <span><strong>{page.title}</strong><small>{page.description}</small></span>
            </button>
          ))}
        </div>
      </section>

      <footer className={styles.notFoundFooter}>
        <p>AURA – Portfolio Risk Intelligence</p>
        <small>© 2026 Aura. All rights reserved.</small>
      </footer>
    </div>
  );
}
