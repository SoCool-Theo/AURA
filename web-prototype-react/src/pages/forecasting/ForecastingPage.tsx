import { useEffect, useRef, useState } from 'react';
import { listPortfolios } from '../../api/portfoliosApi';
import { useAuth } from '../../auth/useAuth';
import { go } from '../../app/routes';
import { Card } from '../../components/ui/Card';
import { AuraSelect } from '../../components/ui/AuraSelect';
import { InlineErrorCard } from '../../components/ui/ApiErrorState';
import type { PortfolioSummaryResponse } from '../../types/portfolio';
import type { ForecastHorizon } from '../../types/forecasting';
import { supportedAssets } from '../portfolios/supportedAssetSymbols';
import { forecastErrorMessage, forecastHorizons } from './forecastingUi';
import { useForecasting } from './useForecasting';
import { ForecastingResults } from './components/ForecastingResults';
import { ForecastHorizonComparison } from './components/ForecastHorizonComparison';
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
  const [horizon, setHorizon] = useState<ForecastHorizon>(30);
  const [compare, setCompare] = useState(false);
  const forecast = useForecasting(scope, scope === 'asset' ? symbol : portfolioId, horizon, compare);

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
    <nav className={styles.analysisNav} aria-label="Analysis views"><button type="button" onClick={() => go(portfolioId ? `analytics/${portfolioId}` : 'analytics')}>Historical Analysis</button><button type="button" aria-current="page" className={styles.active}>Forecast Outlook</button></nav>
    <header className={styles.header}><div><span className={styles.eyebrow}>MODEL-BASED FORECASTING</span><h1>{horizon}-Day Outlook <span className={styles.badge}>{horizon === 30 ? 'V1 Preview' : 'Experimental Weekly V1'}</span></h1><p>Explore model-based return and risk estimates, separate from historical analysis.</p></div><div className={styles.headerActions}>{scope === 'portfolio' && portfolioId && <button type="button" className="secondary-btn" onClick={() => go(`portfolio/${portfolioId}`)}>View Portfolio</button>}{initialScope === 'asset' && initialSelection && <button type="button" className="secondary-btn" onClick={() => go('watchlist')}>Watchlist</button>}<button type="button" className="secondary-btn" disabled={forecast.loading || forecast.comparisonLoading || !(scope === 'asset' ? symbol : portfolioId)} onClick={forecast.refresh}>{forecast.loading || forecast.comparisonLoading ? 'Loading…' : 'Refresh Outlook'}</button></div></header>
    <Card className={styles.controls}>
      <div className={styles.segmented} role="group" aria-label="Outlook scope">{(['portfolio', 'asset'] as const).map(value => <button type="button" key={value} aria-pressed={scope === value} className={scope === value ? styles.active : ''} onClick={() => setScope(value)}>{value === 'portfolio' ? 'Portfolio Outlook' : 'Asset Outlook'}</button>)}</div>
      <div className={styles.controlGrid}>{scope === 'portfolio' ? <div className={styles.field}><span>Portfolio</span><AuraSelect value={portfolioId} options={portfolioOptions} onChange={setPortfolioId} ariaLabel="Select portfolio for forecasting" disabled={loadingList} /></div> : <><label className={styles.field}>Search assets<input value={query} placeholder="Symbol or asset name" onChange={event => setQuery(event.target.value)} /></label><div className={styles.field}><span>Asset</span><AuraSelect value={symbol} options={assetOptions} onChange={setSymbol} ariaLabel="Select asset for forecasting" />{query.trim() && !available.length && <small>No matching assets. Your selected asset is retained.</small>}</div></>}<div className={styles.field}><span>Forecast horizon</span><div className={styles.horizons} role="group" aria-label="Forecast horizon">{forecastHorizons.map(days => <button type="button" key={days} aria-pressed={days === horizon} className={days === horizon ? styles.active : ''} onClick={() => setHorizon(days)} title={`${days} calendar days${days === 30 ? '' : ' · experimental'}`}>{days === 30 ? '30 days' : days / 7 + (days === 7 ? ' week' : ' weeks')}{days !== 30 && <small>Experimental</small>}</button>)}</div></div></div>
      <label className={styles.compareControl}><input type="checkbox" checked={compare} onChange={event => setCompare(event.target.checked)} />Compare all horizons</label>
      <p className={styles.note}>Each horizon uses its own backend model. Weekly V1 has mixed per-asset quality and is not approved as reliable predictions. Refresh reads frozen models and saved market data; it does not retrain or fetch live quotes.</p>
    </Card>
    <p className={styles.education}>Model-based estimates for educational use, not investment advice. Actual outcomes may differ. Prediction ranges are not guarantees or model accuracy scores.</p>
    {scope === 'portfolio' && Boolean(visibleListError) && <InlineErrorCard error={visibleListError} fallbackMessage="Unable to load your portfolios." onRetry={() => setListRevision(value => value + 1)} />}
    {Boolean(forecast.error) && <InlineErrorCard error={forecast.error} message={forecastErrorMessage(forecast.error, scope)} resourceName="Outlook" onRetry={forecast.refresh} onBack={scope === 'portfolio' && portfolioId ? () => go(`portfolio/${portfolioId}`) : undefined} backTitle="Review Portfolio" />}
    {compare && Boolean(scope === 'asset' ? symbol : portfolioId) && <ForecastHorizonComparison results={forecast.outlooks} loading={forecast.comparisonLoading} unavailable={forecast.unavailableHorizons} />}
    {forecast.loading ? <Card className={styles.state}><p role="status">Loading your {horizon}-day {scope} outlook…</p><small>Using saved market data and the configured model artifacts.</small></Card> : forecast.result ? <ForecastingResults key={`${scope}:${scope === 'asset' ? symbol : portfolioId}:${horizon}`} result={forecast.result} showChart={!compare} /> : scope === 'portfolio' && !portfolioId && !loadingList && !visibleListError ? <Card className={styles.state}><h2>No portfolios yet</h2><p>Create a portfolio or explore an asset outlook without one.</p><div className={styles.headerActions}><button type="button" className="primary-btn" onClick={() => go('create')}>Create Portfolio</button><button type="button" className="secondary-btn" onClick={() => setScope('asset')}>Explore Assets</button></div></Card> : scope === 'portfolio' && loadingList && !portfolioId ? <Card className={styles.state}><p role="status">Loading portfolios…</p><button type="button" className="secondary-btn" onClick={() => setScope('asset')}>Explore Assets</button></Card> : null}
  </div>;
}
