import { useEffect, useMemo, useState } from 'react';
import { go } from '../../app/routes';
import {
  deletePortfolio,
  duplicatePortfolio,
  listPortfolios,
  updatePortfolio,
} from '../../api/portfoliosApi';
import { PortfolioCard } from '../../components/portfolio/PortfolioCard';
import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import { AuraSelect } from '../../components/ui/AuraSelect';
import type { AuraSelectOption } from '../../components/ui/AuraSelect';
import type {
  PortfolioResponse,
  PortfolioSummaryResponse,
} from '../../types/portfolio';
import styles from './PortfolioIntegration.module.css';
import { portfolioErrorMessage } from './portfolioUi';

interface PortfolioSummaryProps {
  label: string;
  value: string;
  detail: string;
  icon: string;
  tone: string;
}

const sortOptions: ReadonlyArray<AuraSelectOption<string>> = [
  { value: 'updated', label: 'Recently updated', description: 'Most recently changed portfolios first', icon: 'calendar', tone: 'teal' },
  { value: 'created', label: 'Recently created', description: 'Newest portfolios first', icon: 'calendar', tone: 'blue' },
  { value: 'name', label: 'Portfolio name', description: 'Alphabetical by portfolio name', icon: 'portfolios', tone: 'green' },
];

function PortfolioSummary({ label, value, detail, icon, tone }: PortfolioSummaryProps) {
  return (
    <Card className={`portfolio-summary-card ${tone}`}>
      <span className="summary-icon"><Icon name={icon} size={21} /></span>
      <div><small>{label}</small><strong>{value}</strong><span>{detail}</span></div>
    </Card>
  );
}

function toSummary(portfolio: PortfolioResponse): PortfolioSummaryResponse {
  return {
    id: portfolio.id,
    name: portfolio.name,
    created_at: portfolio.created_at,
    updated_at: portfolio.updated_at,
  };
}

export function PortfoliosPage() {
  const [portfolios, setPortfolios] = useState<PortfolioSummaryResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [query, setQuery] = useState('');
  const [sortBy, setSortBy] = useState('updated');
  const [editing, setEditing] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setLoadError(null);

    void listPortfolios({ signal: controller.signal })
      .then(response => setPortfolios(response.portfolios))
      .catch(error => {
        if (!controller.signal.aborted) {
          setLoadError(portfolioErrorMessage(error, 'Unable to load portfolios.'));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [reloadKey]);

  const visible = useMemo(() => {
    const filtered = portfolios.filter(portfolio => (
      portfolio.name.toLowerCase().includes(query.trim().toLowerCase())
    ));

    return [...filtered].sort((left, right) => {
      if (sortBy === 'name') return left.name.localeCompare(right.name);
      const field = sortBy === 'created' ? 'created_at' : 'updated_at';
      return new Date(right[field]).getTime() - new Date(left[field]).getTime();
    });
  }, [portfolios, query, sortBy]);

  const mostRecentlyUpdated = portfolios.length
    ? new Date(Math.max(...portfolios.map(portfolio => (
      new Date(portfolio.updated_at).getTime()
    )))).toLocaleDateString()
    : '—';

  async function rename(portfolio: PortfolioSummaryResponse) {
    if (busyId) return;
    const name = prompt('New portfolio name', portfolio.name);
    if (!name?.trim() || name.trim() === portfolio.name) return;

    setBusyId(portfolio.id);
    setActionError(null);
    try {
      const updated = await updatePortfolio(portfolio.id, { name: name.trim() });
      setPortfolios(previous => previous.map(item => (
        item.id === portfolio.id ? toSummary(updated) : item
      )));
    } catch (error) {
      setActionError(portfolioErrorMessage(error, 'Unable to rename portfolio.'));
    } finally {
      setBusyId(null);
    }
  }

  async function duplicate(portfolio: PortfolioSummaryResponse) {
    if (busyId) return;
    const name = prompt('Name for duplicated portfolio', `${portfolio.name} Copy`);
    if (!name?.trim()) return;

    setBusyId(portfolio.id);
    setActionError(null);
    try {
      const duplicated = await duplicatePortfolio(portfolio.id, { name: name.trim() });
      setPortfolios(previous => [...previous, toSummary(duplicated)]);
    } catch (error) {
      setActionError(portfolioErrorMessage(error, 'Unable to duplicate portfolio.'));
    } finally {
      setBusyId(null);
    }
  }

  async function remove(portfolio: PortfolioSummaryResponse) {
    if (busyId) return;
    if (!confirm(`Delete ${portfolio.name}? This cannot be undone.`)) return;

    setBusyId(portfolio.id);
    setActionError(null);
    try {
      await deletePortfolio(portfolio.id);
      setPortfolios(previous => previous.filter(item => item.id !== portfolio.id));
    } catch (error) {
      setActionError(portfolioErrorMessage(error, 'Unable to delete portfolio.'));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="page portfolios-page">
      <section className="portfolios-hero">
        <div>
          <h1>Portfolios</h1>
          <p>Create, organize, and monitor the portfolios you use for risk analysis.</p>
        </div>
        <button className="primary-btn new-portfolio-btn" onClick={() => go('create')}>
          <span>＋</span> New Portfolio
        </button>
      </section>

      {!loading && !loadError && <div className="portfolio-summary-grid">
        <PortfolioSummary label="Total Portfolios" value={String(portfolios.length)} detail="Backend portfolio records" icon="portfolios" tone="purple" />
        <PortfolioSummary label="Recently Updated" value={mostRecentlyUpdated} detail="Latest portfolio change" icon="calendar" tone="blue" />
        <PortfolioSummary label="Persistence" value="Aura API" detail="Authenticated backend storage" icon="shield" tone="green" />
      </div>}

      {actionError && <p className={styles.error} role="alert">{actionError}</p>}

      {loading && (
        <Card className={styles.stateCard}><p role="status">Loading your portfolios…</p></Card>
      )}

      {!loading && loadError && (
        <Card className={styles.stateCard}>
          <h2>Unable to load portfolios</h2>
          <p role="alert">{loadError}</p>
          <button className="primary-btn" onClick={() => setReloadKey(key => key + 1)}>Try again</button>
        </Card>
      )}

      {!loading && !loadError && portfolios.length > 0 && <Card className="portfolio-toolbar">
        <label className="portfolio-search">
          <Icon name="search" size={19} />
          <span className="sr-only">Search portfolios</span>
          <input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search portfolios..." />
        </label>
        <div className="portfolio-toolbar-controls">
          <AuraSelect className="portfolio-filter" ariaLabel="Sort portfolios" value={sortBy} options={sortOptions} onChange={setSortBy} />
        </div>
      </Card>}

      {!loading && !loadError && <div className="portfolio-section-heading">
        <div><h2>Your Portfolios</h2><p>{visible.length} of {portfolios.length} portfolios</p></div>
      </div>}
      {!loading && !loadError && portfolios.length === 0 && (
        <Card className={styles.stateCard}>
          <h2>No portfolios yet</h2>
          <p>Create your first named portfolio and save an ordered allocation of symbols and weights.</p>
          <button className="primary-btn" onClick={() => go('create')}>Create portfolio</button>
        </Card>
      )}
      {!loading && !loadError && visible.length > 0 ? (
        <div className="portfolio-grid">
          {visible.map(portfolio => (
            <PortfolioCard
              key={portfolio.id}
              portfolio={portfolio}
              busy={Boolean(busyId)}
              menuOpen={editing === portfolio.id}
              onToggleMenu={() => setEditing(editing === portfolio.id ? null : portfolio.id)}
              onRename={() => { void rename(portfolio); setEditing(null); }}
              onDuplicate={() => { void duplicate(portfolio); setEditing(null); }}
              onDelete={() => { void remove(portfolio); setEditing(null); }}
              onOpenPortfolio={() => go(`portfolio/${portfolio.id}`)}
            />
          ))}
        </div>
      ) : !loading && !loadError && portfolios.length > 0 ? (
        <Card className="portfolio-empty-state">
          <span><Icon name="search" size={25} /></span>
          <h3>No portfolios found</h3>
          <p>Try a different search term.</p>
          <button className="secondary-btn" onClick={() => setQuery('')}>
            Clear search
          </button>
        </Card>
      ) : null}
    </div>
  );
}
