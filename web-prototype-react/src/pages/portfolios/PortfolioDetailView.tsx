import { usePrivateValue } from '../../privacy/PortfolioPrivacy';
import { useEffect, useState } from 'react';
import { MarketDataStatus } from '../../marketData/MarketDataStatus';
import { useMarketDataRefresh } from '../../marketData/useMarketDataRefresh';
import {
  deletePortfolio,
  duplicatePortfolio,
  getPlannedPortfolioPreview,
  getPortfolio,
  getPortfolioValuation,
  updatePortfolio,
} from '../../api/portfoliosApi';
import { listPortfolioReports } from '../../api/reportsApi';
import { go } from '../../app/routes';
import { AllocationLegend } from '../../components/portfolio/AllocationLegend';
import { HoldingsTable } from '../../components/portfolio/HoldingsTable';
import { InlineErrorCard, ScreenErrorState } from '../../components/ui/ApiErrorState';
import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import { SymbolBadge } from '../../components/ui/SymbolBadge';
import type {
  PortfolioCurrency,
  PortfolioPlannedPreviewResponse,
  PortfolioResponse,
  PortfolioValuationResponse,
} from '../../types/portfolio';
import type { PortfolioReportSummary } from '../../types/report';
import { PortfolioHoldingsEditor } from './components/PortfolioHoldingsEditor';
import {
  PortfolioActionDialog,
  type PortfolioAction,
} from './components/PortfolioActionDialog';
import styles from './PortfolioIntegration.module.css';
import {
  formatPortfolioAllocation,
  formatPortfolioDate,
  formatPortfolioMoney,
  isPortfolioMarketDataUnavailable,
  PORTFOLIO_MARKET_DATA_RECOVERY_MESSAGE,
  portfolioValuationErrorMessage,
  portfolioTypeLabel,
  resolvedPortfolioAllocation,
} from './portfolioUi';

type DetailTab = 'Overview' | 'Holdings' | 'Record';

export function PortfolioDetailView({ portfolioId }: { portfolioId?: string }) {
  const privateValue = usePrivateValue();
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [actionError, setActionError] = useState<unknown>(null);
  const [contextError, setContextError] = useState<unknown>(null);
  const [contextLoading, setContextLoading] = useState(false);
  const [valuationCurrency, setValuationCurrency] = useState<PortfolioCurrency>('USD');
  const [valuation, setValuation] = useState<PortfolioValuationResponse | null>(null);
  const [plannedPreview, setPlannedPreview] = useState<PortfolioPlannedPreviewResponse | null>(null);
  const [latestReport, setLatestReport] = useState<PortfolioReportSummary | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [contextReloadKey, setContextReloadKey] = useState(0);
  const [busy, setBusy] = useState(false);
  const [menu, setMenu] = useState(false);
  const [dialogAction, setDialogAction] = useState<PortfolioAction | null>(null);
  const [dialogName, setDialogName] = useState('');
  const [tab, setTab] = useState<DetailTab>('Overview');
  const market = useMarketDataRefresh(() => { if (!busy) setContextReloadKey(value => value + 1); }, portfolio?.id === portfolioId && portfolio?.portfolio_type === 'CURRENT' && Boolean(portfolio.holdings.length));

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
          setLoadError(error);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [portfolioId, reloadKey]);

  useEffect(() => {
    setLatestReport(null);
    if (!portfolioId) return;

    const controller = new AbortController();
    void listPortfolioReports(portfolioId, { signal: controller.signal })
      .then(response => setLatestReport(response.reports[0] ?? null))
      .catch(() => {
        if (!controller.signal.aborted) setLatestReport(null);
      });
    return () => controller.abort();
  }, [portfolioId, reloadKey]);

  useEffect(() => {
    setValuation(null);
    setPlannedPreview(null);
    setContextError(null);
    if (!portfolio || !portfolio.holdings.length || portfolio.portfolio_type === 'LEGACY') {
      setContextLoading(false);
      return;
    }

    const controller = new AbortController();
    setContextLoading(true);
    const request = portfolio.portfolio_type === 'PLANNED'
      ? getPlannedPortfolioPreview(portfolio.id, { signal: controller.signal })
        .then(value => { if (!controller.signal.aborted) setPlannedPreview(value); })
      : getPortfolioValuation(portfolio.id, valuationCurrency, { signal: controller.signal })
        .then(value => { if (!controller.signal.aborted) setValuation(value); });

    void request
      .catch(error => {
        if (!controller.signal.aborted) {
          setContextError(error);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setContextLoading(false);
      });
    return () => controller.abort();
  }, [portfolio, valuationCurrency, contextReloadKey]);

  function openActionDialog(action: PortfolioAction) {
    if (busy || !portfolio) return;
    setMenu(false);
    setActionError(null);
    setDialogName(action === 'duplicate' ? `${portfolio.name} Copy` : portfolio.name);
    setDialogAction(action);
  }

  function closeActionDialog() {
    if (busy) return;
    setDialogAction(null);
    setActionError(null);
  }

  async function submitActionDialog() {
    if (busy || !portfolio || !dialogAction) return;
    const name = dialogName.trim();
    if (dialogAction !== 'delete' && !name) return;
    if (dialogAction === 'rename' && name === portfolio.name) {
      setDialogAction(null);
      return;
    }

    setBusy(true);
    setActionError(null);
    try {
      if (dialogAction === 'rename') {
        setPortfolio(await updatePortfolio(portfolio.id, { name }));
        setDialogAction(null);
      } else if (dialogAction === 'duplicate') {
        const duplicated = await duplicatePortfolio(portfolio.id, { name });
        setDialogAction(null);
        go(`portfolio/${duplicated.id}`);
      } else {
        await deletePortfolio(portfolio.id);
        setDialogAction(null);
        go('portfolios');
      }
    } catch (error) {
      setActionError(error);
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <div className="page portfolio-detail-page"><Card className={styles.stateCard}><p role="status">Loading portfolio…</p></Card></div>;
  }

  if (loadError || !portfolio) return <ScreenErrorState error={loadError ?? 'Portfolio not found.'} fallbackMessage="Unable to retrieve this portfolio." resourceName="Portfolio" onRetry={portfolioId ? () => setReloadKey(key => key + 1) : undefined} onBack={() => go('portfolios')} backTitle="Back to Portfolios" />;

  const allocation = resolvedPortfolioAllocation(portfolio, valuation, plannedPreview);
  const typeLabel = portfolioTypeLabel(portfolio.portfolio_type);
  const totalValueLabel = portfolio.portfolio_type === 'PLANNED'
    ? 'Proposed Investment'
    : portfolio.portfolio_type === 'CURRENT'
      ? 'Current Value'
      : 'Saved Allocation';
  const totalValue = portfolio.portfolio_type === 'PLANNED'
    ? plannedPreview
      ? privateValue(formatPortfolioMoney(plannedPreview.total_proposed_amount, plannedPreview.plan_currency))
      : contextLoading ? 'Loading…' : 'N/A'
    : portfolio.portfolio_type === 'CURRENT'
      ? valuation
        ? privateValue(formatPortfolioMoney(valuation.total_current_value, valuation.valuation_currency))
        : contextLoading ? 'Loading…' : 'N/A'
      : formatPortfolioAllocation(
        portfolio.holdings.reduce((sum, holding) => sum + (holding.weight ?? 0), 0),
      );
  const marketDataUnavailable = isPortfolioMarketDataUnavailable(contextError);

  return (
    <div className="page portfolio-detail-page">
      <button className="detail-back-link" onClick={() => go('portfolios')}>← Back to Portfolios</button>
      <section className="portfolio-detail-header">
        <div className="detail-identity">
          <SymbolBadge symbol={portfolio.name.slice(0, 2).toUpperCase()} />
          <div>
            <div className="detail-title-row"><h1>{portfolio.name}</h1><span className={styles.portfolioTypeBadge}>{typeLabel}</span><button aria-label="Rename portfolio" onClick={() => openActionDialog('rename')} disabled={busy}>✎</button></div>
            <p>Created {formatPortfolioDate(portfolio.created_at)} <span>•</span> Updated {formatPortfolioDate(portfolio.updated_at)}</p>
          </div>
        </div>
        <div className="detail-header-actions">
          <button className="primary-btn" onClick={() => go(`analytics/${portfolio.id}`)} disabled={busy}>Analyze Portfolio</button>
          {latestReport && <button className="secondary-btn" onClick={() => go(`reports/${portfolio.id}/${latestReport.id}`)} disabled={busy}>View Latest Report</button>}
          <button className="secondary-btn" onClick={() => setTab('Holdings')} disabled={busy}>Edit Holdings</button>
          <div className="relative">
            <button className="secondary-btn detail-more-btn" onClick={() => setMenu(!menu)} aria-expanded={menu} disabled={busy}>More <Icon name="chevron-down" size={16} /></button>
            {menu && <div className="menu-pop detail-menu">
              <button onClick={() => openActionDialog('rename')} disabled={busy}>Rename portfolio</button>
              <button onClick={() => openActionDialog('duplicate')} disabled={busy}>Duplicate portfolio</button>
              <button className="danger" onClick={() => openActionDialog('delete')} disabled={busy}>Delete portfolio</button>
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
        {portfolio.portfolio_type === 'CURRENT' && portfolio.holdings.length > 0 && <MarketDataStatus market={market} symbols={[...portfolio.holdings.map(holding => holding.symbol), ...(valuationCurrency === 'THB' ? ['THB=X'] : [])]} busy={busy || contextLoading} />}
        {portfolio.portfolio_type === 'CURRENT' && portfolio.holdings.length > 0 && (
          <div className={styles.valuationToolbar}>
            <div><strong>Current value currency</strong><span>Choose how current values are displayed.</span></div>
            <div className={styles.currencySelector} role="group" aria-label="Current value currency">
              {(['USD', 'THB'] as PortfolioCurrency[]).map(currency => (
                <button type="button" key={currency} className={valuationCurrency === currency ? styles.currencySelected : ''} aria-pressed={valuationCurrency === currency} onClick={() => setValuationCurrency(currency)}>{currency}</button>
              ))}
            </div>
          </div>
        )}

        {Boolean(contextError) && <InlineErrorCard
          error={contextError}
          fallbackMessage={portfolio.portfolio_type === 'PLANNED' ? 'Unable to load the planned portfolio preview.' : 'Unable to load the current portfolio value.'}
          message={portfolio.portfolio_type === 'CURRENT'
            ? portfolioValuationErrorMessage(contextError)
            : undefined}
          stale={marketDataUnavailable || Boolean(valuation) || portfolio.portfolio_type === 'PLANNED'}
          staleMessage={marketDataUnavailable
            ? PORTFOLIO_MARKET_DATA_RECOVERY_MESSAGE
            : undefined}
          onRetry={() => setContextReloadKey(value => value + 1)}
          retryTitle={portfolio.portfolio_type === 'CURRENT' ? 'Retry Current Value' : 'Retry preview'}
          compactAction={portfolio.portfolio_type === 'CURRENT'}
        />}

        <div className={`${styles.metadataGrid} ${styles.overviewMetrics}`}>
          <div><small>Holdings</small><strong>{portfolio.holdings.length}</strong></div>
          <div><small>Type</small><strong>{typeLabel}</strong></div>
          <div><small>{totalValueLabel}</small><strong>{totalValue}</strong></div>
          <div><small>Portfolio ID</small><strong>{portfolio.id}</strong></div>
        </div>
        {portfolio.holdings.length > 0 ? <>
          {allocation.length > 0 ? (
            <Card className={`detail-section-card ${styles.allocationCard}`}><AllocationLegend holdings={allocation} label={portfolio.portfolio_type === 'PLANNED' ? 'Target Allocation' : portfolio.portfolio_type === 'CURRENT' ? 'Current Allocation' : 'Saved Allocation'} /></Card>
          ) : (
            <Card className={styles.stateCard}>
              <h2>{contextLoading ? 'Loading allocation…' : 'Allocation unavailable'}</h2>
              <p>{portfolio.portfolio_type === 'PLANNED'
                ? 'Target allocation will appear when the planned preview is available.'
                : portfolio.portfolio_type === 'CURRENT'
                  ? 'Current allocation will appear when market valuation is available.'
                  : 'No saved allocation is available.'}</p>
            </Card>
          )}
          <HoldingsTable portfolio={portfolio} valuation={valuation} plannedPreview={plannedPreview} onViewAll={() => setTab('Holdings')} />
          {portfolio.portfolio_type === 'PLANNED' && plannedPreview && (
            <p className={styles.hypotheticalNotice}>This is a hypothetical plan. Estimated shares are display-only and do not affect allocation or analysis.</p>
          )}
          {portfolio.portfolio_type === 'CURRENT' && valuation && (
            <p className={styles.valuationMeta}>Prices range from {valuation.oldest_price_as_of} to {valuation.newest_price_as_of}. Valuation requested {valuation.requested_date}.</p>
          )}
        </> : <Card className={styles.stateCard}><h2>No holdings saved</h2><p>{portfolio.portfolio_type === 'PLANNED' ? 'Add proposed amounts to complete this plan.' : 'Add ownership details to complete this portfolio.'}</p><button className="primary-btn" onClick={() => setTab('Holdings')}>Add holdings</button></Card>}
      </div>}

      {tab === 'Holdings' && <PortfolioHoldingsEditor portfolio={portfolio} onSaved={updated => { setPortfolio(updated); setActionError(null); }} />}

      {tab === 'Record' && <div className="detail-tab-panel"><Card className={`detail-section-card ${styles.recordCard}`}><div className="detail-section-header"><div><h2>Portfolio Record</h2><p>Saved identity and portfolio mode.</p></div></div><div className={`${styles.metadataGrid} ${styles.recordGrid}`}><div><small>Name</small><strong>{portfolio.name}</strong></div><div><small>Type</small><strong>{typeLabel}</strong></div><div><small>Plan Currency</small><strong>{portfolio.plan_currency ?? 'Not applicable'}</strong></div><div><small>Created</small><strong>{formatPortfolioDate(portfolio.created_at)}</strong></div><div><small>Updated</small><strong>{formatPortfolioDate(portfolio.updated_at)}</strong></div></div></Card></div>}

      {dialogAction && <PortfolioActionDialog
        action={dialogAction}
        portfolioName={portfolio.name}
        value={dialogName}
        busy={busy}
        error={actionError}
        onValueChange={value => {
          setDialogName(value);
          setActionError(null);
        }}
        onCancel={closeActionDialog}
        onSubmit={() => void submitActionDialog()}
      />}
    </div>
  );
}
