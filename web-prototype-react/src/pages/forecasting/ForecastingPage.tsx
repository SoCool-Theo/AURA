import { useEffect, useRef, useState } from 'react';
import { listPortfolios } from '../../api/portfoliosApi';
import { useAuth } from '../../auth/useAuth';
import { go } from '../../app/routes';
import { Card } from '../../components/ui/Card';
import { AuraSelect } from '../../components/ui/AuraSelect';
import { InlineErrorCard } from '../../components/ui/ApiErrorState';
import type { PortfolioSummaryResponse } from '../../types/portfolio';
import { supportedAssets } from '../portfolios/supportedAssetSymbols';
import { forecastErrorMessage, forecastHorizons } from './forecastingUi';
import { useForecasting } from './useForecasting';
import { ForecastingResults } from './components/ForecastingResults';
import styles from './Forecasting.module.css';

export function ForecastingPage({ scope: initialScope = 'portfolio', selection: initialSelection }: { scope?: 'portfolio' | 'asset'; selection?: string }) {
  const { user, status } = useAuth();
  const account = status === 'authenticated' ? user?.id : undefined;
  const identity = useRef(account); identity.current = account;
  const [scope, setScope] = useState(initialScope);
  const [portfolioId, setPortfolioId] = useState(initialScope === 'portfolio' ? initialSelection ?? '' : '');
  const [symbol, setSymbol] = useState(initialScope === 'asset' ? initialSelection?.trim().toUpperCase() || 'AAPL' : 'AAPL');
  const [query, setQuery] = useState('');
  const [list, setList] = useState<{ account?: string; items: PortfolioSummaryResponse[]; loading: boolean; error: unknown }>({ items: [], loading: true, error: null });
  const [listRevision, setListRevision] = useState(0);
  const forecast = useForecasting(scope, scope === 'asset' ? symbol : portfolioId);

  useEffect(() => {
    if (!account) return;
    const controller = new AbortController();
    const current = () => !controller.signal.aborted && identity.current === account;
    setList({ account, items: [], loading: true, error: null });
    const timeout = setTimeout(() => {
      if (current()) setList({ account, items: [], loading: false, error: new Error('Portfolio list timed out') });
      controller.abort();
    }, 20000);
    void listPortfolios({ signal: controller.signal }).then(response => {
      if (!current()) return;
      setList({ account, items: response.portfolios, loading: false, error: null });
      setPortfolioId(value => value || response.portfolios[0]?.id || '');
    }).catch(error => {
      if (current()) setList({ account, items: [], loading: false, error });
    }).finally(() => clearTimeout(timeout));
    return () => { controller.abort(); clearTimeout(timeout); };
  }, [account, listRevision]);

  const portfolios = list.account === account ? list.items : [];
  const visibleListError = list.account === account ? list.error : null;
  const loadingList = list.account !== account || list.loading;
  const available = supportedAssets.filter(asset => `${asset.symbol} ${asset.name}`.toLowerCase().includes(query.trim().toLowerCase()));
  const assetOptions = available.map(asset => ({ value: asset.symbol as string, label: `${asset.symbol} · ${asset.name}`, icon: 'trend', tone: 'teal' as const }));
  // Keep the selected asset visible even if a new search excludes it.
  if (!assetOptions.some(option => option.value === symbol)) assetOptions.unshift({ value: symbol, label: symbol, icon: 'trend', tone: 'teal' });
  const portfolioOptions = [
    { value: portfolioId && !portfolios.some(item => item.id === portfolioId) ? portfolioId : '', label: loadingList ? 'Loading portfolios…' : portfolioId && !portfolios.some(item => item.id === portfolioId) ? 'Portfolio unavailable' : 'Select a portfolio', disabled: true },
    ...portfolios.map(item => ({ value: item.id, label: item.name, description: item.portfolio_type === 'PLANNED' ? 'Planned target allocation · hypothetical' : item.portfolio_type === 'LEGACY' ? 'Legacy saved allocation' : 'Current holdings', icon: 'wallet', tone: 'teal' as const })),
  ];

  return <div className={`page ${styles.page}`}>
    <nav className={styles.analysisNav} aria-label="Analysis views"><button type="button" onClick={() => go(portfolioId ? `analytics/${portfolioId}` : 'analytics')}>Historical Analysis</button><button type="button" aria-current="page" className={styles.active}>30-Day Outlook</button></nav>
    <header className={styles.header}><div><span className={styles.eyebrow}>MODEL-BASED FORECASTING</span><h1>30-Day Outlook <span className={styles.badge}>V1 Preview</span></h1><p>Explore model-based return and risk estimates, separate from historical analysis.</p></div><div className={styles.headerActions}>{scope === 'portfolio' && portfolioId && <button type="button" className="secondary-btn" onClick={() => go(`portfolio/${portfolioId}`)}>View Portfolio</button>}{initialScope === 'asset' && initialSelection && <button type="button" className="secondary-btn" onClick={() => go('watchlist')}>Watchlist</button>}<button type="button" className="secondary-btn" disabled={forecast.loading || !(scope === 'asset' ? symbol : portfolioId)} onClick={forecast.refresh}>{forecast.loading ? 'Loading…' : 'Refresh Outlook'}</button></div></header>
    <Card className={styles.controls}>
      <div className={styles.segmented} role="group" aria-label="Outlook scope">{(['portfolio', 'asset'] as const).map(value => <button type="button" key={value} aria-pressed={scope === value} className={scope === value ? styles.active : ''} onClick={() => setScope(value)}>{value === 'portfolio' ? 'Portfolio Outlook' : 'Asset Outlook'}</button>)}</div>
      <div className={styles.controlGrid}>{scope === 'portfolio' ? <div className={styles.field}><span>Portfolio</span><AuraSelect value={portfolioId} options={portfolioOptions} onChange={setPortfolioId} ariaLabel="Select portfolio for forecasting" disabled={loadingList} /></div> : <><label className={styles.field}>Search assets<input value={query} placeholder="Symbol or asset name" onChange={event => setQuery(event.target.value)} /></label><div className={styles.field}><span>Asset</span><AuraSelect value={symbol} options={assetOptions} onChange={setSymbol} ariaLabel="Select asset for forecasting" />{query.trim() && !available.length && <small>No matching assets. Your selected asset is retained.</small>}</div></>}<div className={styles.field}><span>Forecast horizon</span><div className={styles.horizons} role="group" aria-label="Forecast horizon">{forecastHorizons.map(days => <button type="button" key={days} disabled={days !== 30} aria-pressed={days === 30} className={days === 30 ? styles.active : ''} title={days === 30 ? '30 calendar days' : 'Requires a validated model for this horizon'}>{days === 30 ? '30 days' : days / 7 + (days === 7 ? ' week' : ' weeks')}{days !== 30 && <small>Not available</small>}</button>)}</div></div></div>
      <p className={styles.note}>V1 supports 30 calendar days only. Weekly horizons will be enabled after their backend models are validated. Refresh reads the configured frozen model; it does not retrain it.</p>
    </Card>
    <p className={styles.education}>Model-based estimates for educational use, not investment advice. Actual outcomes may differ. Prediction ranges are not guarantees or model accuracy scores.</p>
    {scope === 'portfolio' && Boolean(visibleListError) && <InlineErrorCard error={visibleListError} fallbackMessage="Unable to load your portfolios." onRetry={() => setListRevision(value => value + 1)} />}
    {Boolean(forecast.error) && <InlineErrorCard error={forecast.error} message={forecastErrorMessage(forecast.error, scope)} resourceName="Outlook" onRetry={forecast.refresh} onBack={scope === 'portfolio' && portfolioId ? () => go(`portfolio/${portfolioId}`) : undefined} backTitle="Review Portfolio" />}
    {forecast.loading ? <Card className={styles.state}><p role="status">Loading your {scope} outlook…</p><small>Using saved market data and the configured model artifacts.</small></Card> : forecast.result ? <ForecastingResults key={`${scope}:${scope === 'asset' ? symbol : portfolioId}`} result={forecast.result} /> : scope === 'portfolio' && !portfolioId && !loadingList && !visibleListError ? <Card className={styles.state}><h2>No portfolios yet</h2><p>Create a portfolio or explore an asset outlook without one.</p><div className={styles.headerActions}><button type="button" className="primary-btn" onClick={() => go('create')}>Create Portfolio</button><button type="button" className="secondary-btn" onClick={() => setScope('asset')}>Explore Assets</button></div></Card> : scope === 'portfolio' && loadingList && !portfolioId ? <Card className={styles.state}><p role="status">Loading portfolios…</p><button type="button" className="secondary-btn" onClick={() => setScope('asset')}>Explore Assets</button></Card> : null}
  </div>;
}
