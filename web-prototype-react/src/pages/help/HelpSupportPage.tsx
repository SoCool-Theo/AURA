import { useEffect, useState } from 'react';
import { go } from '../../app/routes';
import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import { filterHelpSections } from './helpContent';
import styles from './HelpSupportPage.module.css';

export function HelpSupportPage() {
  const [query, setQuery] = useState('');
  const sections = filterHelpSections(query);
  const count = sections.reduce((total, section) => total + section.articles.length, 0);

  useEffect(() => { window.scrollTo({ top: 0 }); }, []);

  return <div className={`page ${styles.page}`}>
    <button type="button" className={styles.back} onClick={() => go('settings')}>
      <span aria-hidden="true">←</span> Back to Settings
    </button>
    <header className={styles.header}>
      <span className={styles.eyebrow}>AURA SUPPORT CENTER</span>
      <h1>Help &amp; Support</h1>
      <p>Find clear answers about portfolios, results, privacy, and using Aura.</p>
    </header>
    <Card className={styles.searchCard}>
      <label className={styles.search}>
        <Icon name="search" size={20} />
        <span className="sr-only">Search help articles</span>
        <input type="search" value={query} onChange={event => setQuery(event.target.value)}
          placeholder="Search questions, features, or error messages…" />
      </label>
      <p className={styles.results} role="status">{count} {count === 1 ? 'article' : 'articles'}{query.trim() ? ' found' : ' available'} · Select a question to read the answer.</p>
    </Card>
    <div className={styles.sections}>
      {sections.map(section => <Card className={styles.section} key={section.id}>
        <section aria-labelledby={`help-${section.id}`}>
          <h2 id={`help-${section.id}`}>{section.title}</h2>
          {section.articles.map(article => <details key={article.id} className={styles.article}>
            <summary>{article.question}<span className={styles.chevron}><Icon name="chevron-down" size={18} /></span></summary>
            <div className={styles.answer}>{article.answer.map((paragraph, index) => <p key={index}>{paragraph}</p>)}</div>
          </details>)}
        </section>
      </Card>)}
    </div>
    {count === 0 && <Card className={styles.empty}>
      <Icon name="search" size={26} /><h2>No matching help articles</h2>
      <p>Try a topic such as “portfolio”, “privacy”, or “simulation”.</p>
      <button type="button" className="secondary-btn" onClick={() => setQuery('')}>Clear search</button>
    </Card>}
    <footer className={styles.boundary}><Icon name="shield" size={18} />
      <p>Aura is a portfolio risk education platform. Its guidance and historical results are not financial or investment advice.</p>
    </footer>
  </div>;
}
