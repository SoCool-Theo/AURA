import { useEffect, useMemo, useState } from 'react';
import { go } from '../../app/routes';
import {
  deletePortfolio,
  duplicatePortfolio,
  listPortfolios,
  updatePortfolio,
} from '../../api/portfoliosApi';
import { listPortfolioReports } from '../../api/reportsApi';
import { PortfolioCard } from '../../components/portfolio/PortfolioCard';
import { ScreenErrorState } from '../../components/ui/ApiErrorState';
import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import { AuraSelect } from '../../components/ui/AuraSelect';
import type { AuraSelectOption } from '../../components/ui/AuraSelect';
import type {
  PortfolioResponse,
  PortfolioSummaryResponse,
} from '../../types/portfolio';
import type { PortfolioReportSummary } from '../../types/report';
import { PortfolioActionDialog, type PortfolioAction } from './components/PortfolioActionDialog';
import styles from './PortfolioIntegration.module.css';

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
    portfolio_type: portfolio.portfolio_type,
    plan_currency: portfolio.plan_currency,
    created_at: portfolio.created_at,
    updated_at: portfolio.updated_at,
  };
}

export function PortfoliosPage() {
  const [portfolios, setPortfolios] = useState<PortfolioSummaryResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [query, setQuery] = useState('');
  const [sortBy, setSortBy] = useState('updated');
  const [editing, setEditing] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [latestReports, setLatestReports] = useState<Map<string, PortfolioReportSummary>>(new Map());
  const [reportLookupError, setReportLookupError] = useState(false);
  const [dialogAction, setDialogAction] = useState<PortfolioAction | null>(null);
  const [dialogPortfolio, setDialogPortfolio] = useState<PortfolioSummaryResponse | null>(null);
  const [dialogName, setDialogName] = useState('');
  const [dialogError, setDialogError] = useState<unknown>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setLoadError(null);

    void listPortfolios({ signal: controller.signal })
      .then(response => setPortfolios(response.portfolios))
      .catch(error => {
        if (!controller.signal.aborted) {
          setLoadError(error);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [reloadKey]);

  const portfolioIds = portfolios.map(portfolio => portfolio.id).join('|');

  useEffect(() => {
    setLatestReports(new Map());
    setReportLookupError(false);
    if (!portfolios.length) return;

    const controller = new AbortController();
    void Promise.allSettled(portfolios.map(async portfolio => ({
      portfolioId: portfolio.id,
      reports: (await listPortfolioReports(portfolio.id, {
        signal: controller.signal,
      })).reports,
    }))).then(results => {
      if (controller.signal.aborted) return;
      const next = new Map<string, PortfolioReportSummary>();
      let failed = false;
      for (const result of results) {
        if (result.status === 'rejected') {
          failed = true;
          continue;
        }
        const latest = result.value.reports[0];
        if (latest) next.set(result.value.portfolioId, latest);
      }
      setLatestReports(next);
      setReportLookupError(failed);
    });
    return () => controller.abort();
  }, [portfolioIds]);

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

  function openActionDialog(action: PortfolioAction, portfolio: PortfolioSummaryResponse) {
    if (busyId) return;
    setEditing(null);
    setDialogAction(action);
    setDialogPortfolio(portfolio);
    setDialogName(action === 'duplicate' ? `${portfolio.name} Copy` : portfolio.name);
    setDialogError(null);
  }

  function closeActionDialog() {
    if (busyId) return;
    setDialogAction(null);
    setDialogPortfolio(null);
    setDialogError(null);
  }

  async function submitActionDialog() {
    if (busyId || !dialogAction || !dialogPortfolio) return;
    const name = dialogName.trim();
    if (dialogAction !== 'delete' && !name) return;
    if (dialogAction === 'rename' && name === dialogPortfolio.name) {
      closeActionDialog();
      return;
    }
    setBusyId(dialogPortfolio.id);
    setDialogError(null);
    try {
      if (dialogAction === 'rename') {
        const updated = await updatePortfolio(dialogPortfolio.id, { name });
        setPortfolios(previous => previous.map(item => item.id === dialogPortfolio.id ? toSummary(updated) : item));
      } else if (dialogAction === 'duplicate') {
        const duplicated = await duplicatePortfolio(dialogPortfolio.id, { name });
        setPortfolios(previous => [...previous, toSummary(duplicated)]);
      } else {
        await deletePortfolio(dialogPortfolio.id);
        setPortfolios(previous => previous.filter(item => item.id !== dialogPortfolio.id));
      }
      setDialogAction(null);
      setDialogPortfolio(null);
    } catch (error) {
      setDialogError(error);
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
        <PortfolioSummary label="Total Portfolios" value={String(portfolios.length)} detail="Saved portfolios" icon="portfolios" tone="purple" />
        <PortfolioSummary label="Recently Updated" value={mostRecentlyUpdated} detail="Latest portfolio change" icon="calendar" tone="blue" />
        <PortfolioSummary label="Access" value="Private" detail="Available only in your account" icon="shield" tone="green" />
      </div>}

      {reportLookupError && <p className={styles.contextNotice} role="alert">Some latest-report shortcuts are temporarily unavailable. Portfolios can still be opened normally.</p>}

      {loading && (
        <Card className={styles.stateCard}><p role="status">Loading your portfolios…</p></Card>
      )}

      {!loading && Boolean(loadError) && <ScreenErrorState error={loadError} fallbackMessage="Unable to load your portfolios." resourceName="Portfolio list" onRetry={() => setReloadKey(key => key + 1)} />}

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
          <p>Create a Current portfolio for investments you own or a Planned portfolio to evaluate before investing.</p>
          <button className="primary-btn" onClick={() => go('create')}>Create portfolio</button>
        </Card>
      )}
      {!loading && !loadError && visible.length > 0 ? (
        <div className="portfolio-grid">
          {visible.map(portfolio => {
            const latestReport = latestReports.get(portfolio.id);
            return (
            <PortfolioCard
              key={portfolio.id}
              portfolio={portfolio}
              busy={Boolean(busyId)}
              menuOpen={editing === portfolio.id}
              onToggleMenu={() => setEditing(editing === portfolio.id ? null : portfolio.id)}
              onRename={() => openActionDialog('rename', portfolio)}
              onDuplicate={() => openActionDialog('duplicate', portfolio)}
              onDelete={() => openActionDialog('delete', portfolio)}
              onOpenPortfolio={() => go(`portfolio/${portfolio.id}`)}
              onOpenLatestReport={latestReport
                ? () => go(`reports/${portfolio.id}/${latestReport.id}`)
                : undefined}
            />
            );
          })}
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
      {dialogAction && dialogPortfolio && <PortfolioActionDialog
        action={dialogAction}
        portfolioName={dialogPortfolio.name}
        value={dialogName}
        busy={busyId === dialogPortfolio.id}
        error={dialogError}
        onValueChange={value => { setDialogName(value); setDialogError(null); }}
        onCancel={closeActionDialog}
        onSubmit={() => void submitActionDialog()}
      />}
    </div>
  );
}
