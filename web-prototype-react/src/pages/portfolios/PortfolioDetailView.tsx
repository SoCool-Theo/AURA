import { useEffect, useState } from 'react';
import {
  deletePortfolio,
  duplicatePortfolio,
  getPortfolio,
  updatePortfolio,
} from '../../api/portfoliosApi';
import { go } from '../../app/routes';
import { AllocationLegend } from '../../components/portfolio/AllocationLegend';
import { HoldingsTable } from '../../components/portfolio/HoldingsTable';
import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import { SymbolBadge } from '../../components/ui/SymbolBadge';
import type { PortfolioResponse } from '../../types/portfolio';
import { PortfolioHoldingsEditor } from './components/PortfolioHoldingsEditor';
import styles from './PortfolioIntegration.module.css';
import { formatPortfolioDate, portfolioErrorMessage } from './portfolioUi';

type DetailTab = 'Overview' | 'Holdings' | 'Record';

export function PortfolioDetailView({ portfolioId }: { portfolioId?: string }) {
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [busy, setBusy] = useState(false);
  const [menu, setMenu] = useState(false);
  const [tab, setTab] = useState<DetailTab>('Overview');

  useEffect(() => {
    if (!portfolioId) {
      setLoadError('Portfolio not found');
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    setLoading(true);
    setLoadError(null);
    void getPortfolio(portfolioId, { signal: controller.signal })
      .then(setPortfolio)
      .catch(error => {
        if (!controller.signal.aborted) {
          setLoadError(portfolioErrorMessage(error, 'Unable to retrieve portfolio.'));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [portfolioId, reloadKey]);

  async function rename() {
    if (busy) return;
    if (!portfolio) return;
    const name = prompt('New portfolio name', portfolio.name);
    if (!name?.trim() || name.trim() === portfolio.name) return;

    setBusy(true);
    setActionError(null);
    try {
      setPortfolio(await updatePortfolio(portfolio.id, { name: name.trim() }));
    } catch (error) {
      setActionError(portfolioErrorMessage(error, 'Unable to rename portfolio.'));
    } finally {
      setBusy(false);
    }
  }

  async function duplicate() {
    if (busy) return;
    if (!portfolio) return;
    const name = prompt('Name for duplicated portfolio', `${portfolio.name} Copy`);
    if (!name?.trim()) return;

    setBusy(true);
    setActionError(null);
    try {
      const duplicated = await duplicatePortfolio(portfolio.id, { name: name.trim() });
      go(`portfolio/${duplicated.id}`);
    } catch (error) {
      setActionError(portfolioErrorMessage(error, 'Unable to duplicate portfolio.'));
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (busy) return;
    if (!portfolio || !confirm(`Delete ${portfolio.name}? This cannot be undone.`)) return;

    setBusy(true);
    setActionError(null);
    try {
      await deletePortfolio(portfolio.id);
      setPortfolio(null);
      go('portfolios');
    } catch (error) {
      setActionError(portfolioErrorMessage(error, 'Unable to delete portfolio.'));
      setBusy(false);
    }
  }

  if (loading) {
    return <div className="page portfolio-detail-page"><Card className={styles.stateCard}><p role="status">Loading portfolio…</p></Card></div>;
  }

  if (loadError || !portfolio) {
    return (
      <div className="page portfolio-detail-page">
        <button className="detail-back-link" onClick={() => go('portfolios')}>← Back to Portfolios</button>
        <Card className={styles.stateCard}>
          <h1>Portfolio unavailable</h1>
          <p role="alert">{loadError || 'Portfolio not found'}</p>
          {portfolioId && <button className="primary-btn" onClick={() => setReloadKey(key => key + 1)}>Try again</button>}
        </Card>
      </div>
    );
  }

  const totalPercentage = portfolio.holdings.reduce((sum, holding) => (
    sum + (holding.weight == null ? 0 : holding.weight * 100)
  ), 0);

  return (
    <div className="page portfolio-detail-page">
      <button className="detail-back-link" onClick={() => go('portfolios')}>← Back to Portfolios</button>
      {actionError && <p className={styles.error} role="alert">{actionError}</p>}
      <section className="portfolio-detail-header">
        <div className="detail-identity">
          <SymbolBadge symbol={portfolio.name.slice(0, 2).toUpperCase()} />
          <div>
            <div className="detail-title-row"><h1>{portfolio.name}</h1><button aria-label="Rename portfolio" onClick={() => void rename()} disabled={busy}>✎</button></div>
            <p>Created {formatPortfolioDate(portfolio.created_at)} <span>•</span> Updated {formatPortfolioDate(portfolio.updated_at)}</p>
          </div>
        </div>
        <div className="detail-header-actions">
          <button className="primary-btn" onClick={() => setTab('Holdings')} disabled={busy}>Edit Holdings</button>
          <div className="relative">
            <button className="secondary-btn detail-more-btn" onClick={() => setMenu(!menu)} aria-expanded={menu} disabled={busy}>More <Icon name="chevron-down" size={16} /></button>
            {menu && <div className="menu-pop detail-menu">
              <button onClick={() => { setMenu(false); void rename(); }} disabled={busy}>Rename portfolio</button>
              <button onClick={() => { setMenu(false); void duplicate(); }} disabled={busy}>Duplicate portfolio</button>
              <button className="danger" onClick={() => { setMenu(false); void remove(); }} disabled={busy}>Delete portfolio</button>
            </div>}
          </div>
        </div>
      </section>

      <nav className="detail-tabs" aria-label="Portfolio sections" role="tablist">
        {(['Overview', 'Holdings', 'Record'] as DetailTab[]).map(item => (
          <button role="tab" aria-selected={tab === item} className={tab === item ? 'active' : ''} onClick={() => setTab(item)} key={item}>
            {item}{item === 'Holdings' && <span>{portfolio.holdings.length}</span>}
          </button>
        ))}
      </nav>

      {tab === 'Overview' && <div className="detail-tab-panel">
        <div className={styles.metadataGrid}>
          <div><small>Holdings</small><strong>{portfolio.holdings.length}</strong></div>
          <div><small>Total Allocation</small><strong>{Number(totalPercentage.toFixed(10))}%</strong></div>
          <div><small>Portfolio ID</small><strong>{portfolio.id}</strong></div>
        </div>
        {portfolio.holdings.length > 0 ? <>
          <Card className="detail-section-card"><AllocationLegend holdings={portfolio.holdings} /></Card>
          <HoldingsTable portfolio={portfolio} onViewAll={() => setTab('Holdings')} />
        </> : <Card className={styles.stateCard}><h2>No holdings saved</h2><p>This portfolio exists. Add a complete ordered allocation in the Holdings tab.</p><button className="primary-btn" onClick={() => setTab('Holdings')}>Add holdings</button></Card>}
      </div>}

      {tab === 'Holdings' && <PortfolioHoldingsEditor portfolio={portfolio} onSaved={updated => { setPortfolio(updated); setActionError(null); }} />}

      {tab === 'Record' && <div className="detail-tab-panel"><Card className="detail-section-card"><div className="detail-section-header"><div><h2>Backend Portfolio Record</h2><p>Only fields returned by the Portfolio API are shown.</p></div></div><div className={styles.metadataGrid}><div><small>Name</small><strong>{portfolio.name}</strong></div><div><small>Created</small><strong>{formatPortfolioDate(portfolio.created_at)}</strong></div><div><small>Updated</small><strong>{formatPortfolioDate(portfolio.updated_at)}</strong></div></div></Card></div>}
    </div>
  );
}
