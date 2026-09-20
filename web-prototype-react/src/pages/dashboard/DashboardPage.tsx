import { useEffect, useState } from 'react';
import {
  getPlannedPortfolioAllocation,
  getPortfolio,
  getPortfolioValuation,
  listPortfolios,
} from '../../api/portfoliosApi';
import { getPortfolioReport, listPortfolioReports } from '../../api/reportsApi';
import { useAuth } from '../../auth/useAuth';
import { go } from '../../app/routes';
import { InlineErrorCard, ScreenErrorState } from '../../components/ui/ApiErrorState';
import { Card } from '../../components/ui/Card';
import type {
  PortfolioCurrency,
  PortfolioPlannedAllocationResponse,
  PortfolioResponse,
  PortfolioSummaryResponse,
  PortfolioValuationResponse,
} from '../../types/portfolio';
import type { PortfolioReportResponse } from '../../types/report';
import {
  isPortfolioMarketDataUnavailable,
  PORTFOLIO_MARKET_DATA_RECOVERY_MESSAGE,
  portfolioValuationErrorMessage,
  resolvedPortfolioAllocation,
} from '../portfolios/portfolioUi';
import styles from './DashboardIntegration.module.css';
import { AiInsight } from './components/AiInsight';
import { DashboardHeader } from './components/DashboardHeader';
import { DashboardKpiGrid } from './components/DashboardKpiGrid';
import { PortfolioAllocation } from './components/PortfolioAllocation';
import { PortfolioAnalysisCard } from './components/PortfolioAnalysisCard';
import { PortfolioPerformance } from './components/PortfolioPerformance';
import { PortfolioSelector } from './components/PortfolioSelector';
import { RiskDrivers } from './components/RiskDrivers';

export function DashboardPage() {
  const { user } = useAuth();
  const [portfolios, setPortfolios] = useState<PortfolioSummaryResponse[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);
  const [report, setReport] = useState<PortfolioReportResponse | null>(null);
  const [valuationCurrency, setValuationCurrency] = useState<PortfolioCurrency>('USD');
  const [valuation, setValuation] = useState<PortfolioValuationResponse | null>(null);
  const [plannedAllocation, setPlannedAllocation] = useState<PortfolioPlannedAllocationResponse | null>(null);
  const [listLoading, setListLoading] = useState(true);
  const [portfolioLoading, setPortfolioLoading] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [listError, setListError] = useState<unknown>(null);
  const [portfolioError, setPortfolioError] = useState<unknown>(null);
  const [reportError, setReportError] = useState<unknown>(null);
  const [contextLoading, setContextLoading] = useState(false);
  const [contextError, setContextError] = useState<unknown>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [reportReloadKey, setReportReloadKey] = useState(0);
  const [contextReloadKey, setContextReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController(); setListLoading(true); setListError(null); setPortfolios([]); setSelectedId('');
    void listPortfolios({ signal: controller.signal }).then(response => { setPortfolios(response.portfolios); setSelectedId(response.portfolios[0]?.id ?? ''); }).catch(error => { if (!controller.signal.aborted) setListError(error); }).finally(() => { if (!controller.signal.aborted) setListLoading(false); });
    return () => controller.abort();
  }, [reloadKey]);

  useEffect(() => {
    setPortfolio(null); setReport(null); setPortfolioError(null); setReportError(null);
    if (!selectedId) { setPortfolioLoading(false); setReportLoading(false); return; }
    const controller = new AbortController(); setPortfolioLoading(true); setReportLoading(true);
    void getPortfolio(selectedId, { signal: controller.signal }).then(setPortfolio).catch(error => { if (!controller.signal.aborted) setPortfolioError(error); }).finally(() => { if (!controller.signal.aborted) setPortfolioLoading(false); });
    void listPortfolioReports(selectedId, { signal: controller.signal }).then(async response => {
      const latest = response.reports[0];
      if (!latest) return;
      const detail = await getPortfolioReport(selectedId, latest.id, { signal: controller.signal });
      if (!controller.signal.aborted) setReport(detail);
    }).catch(error => { if (!controller.signal.aborted) setReportError(error); }).finally(() => { if (!controller.signal.aborted) setReportLoading(false); });
    return () => controller.abort();
  }, [selectedId, reportReloadKey]);

  useEffect(() => {
    setValuation(null);
    setPlannedAllocation(null);
    setContextError(null);
    if (!portfolio || !portfolio.holdings.length || portfolio.portfolio_type === 'LEGACY') {
      setContextLoading(false);
      return;
    }

    const controller = new AbortController();
    setContextLoading(true);
    const request = portfolio.portfolio_type === 'PLANNED'
      ? getPlannedPortfolioAllocation(portfolio.id, { signal: controller.signal })
        .then(setPlannedAllocation)
      : getPortfolioValuation(portfolio.id, valuationCurrency, { signal: controller.signal })
        .then(setValuation);

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

  function selectPortfolio(nextId: string) {
    if (nextId === selectedId) return;
    setPortfolio(null); setReport(null); setValuation(null); setPlannedAllocation(null); setPortfolioError(null); setReportError(null); setContextError(null);
    setPortfolioLoading(true); setReportLoading(true); setSelectedId(nextId);
  }

  const firstName = user?.email.split('@')[0] || 'Investor';
  if (listLoading) return <Card className={styles.state}><h2>Loading Dashboard</h2><p role="status">Loading your portfolios.</p></Card>;
  if (listError) return <ScreenErrorState error={listError} fallbackMessage="Unable to load your dashboard portfolios." resourceName="Dashboard" onRetry={() => setReloadKey(value => value + 1)} />;
  if (!portfolios.length) return <Card className={styles.state}><h2>No portfolios yet</h2><p>Create a Current portfolio for investments you own or a Planned portfolio to evaluate before investing.</p><button className="primary-btn" onClick={() => go('create')}>Create Portfolio</button></Card>;

  const allocation = portfolio
    ? resolvedPortfolioAllocation(portfolio, valuation, plannedAllocation)
    : [];
  const marketDataUnavailable = isPortfolioMarketDataUnavailable(contextError);

  return <div className="page dashboard-page">
    <DashboardHeader firstName={firstName} report={report} />
    {Boolean(portfolioError) && <InlineErrorCard error={portfolioError} fallbackMessage="Unable to load the selected portfolio." resourceName="Portfolio" onRetry={() => setReportReloadKey(value => value + 1)} />}
    {portfolioLoading && <Card className={styles.state}><h2>Loading selected portfolio</h2><p role="status">Loading its holdings and saved analysis.</p></Card>}
    {!portfolioLoading && !portfolio && !portfolioError && <Card className={styles.state}><h2>Portfolio unavailable</h2><p>The selected portfolio could not be displayed.</p></Card>}
    {portfolio && <>
      <div className={styles.portfolioContextBar}>
        <PortfolioSelector portfolios={portfolios} selectedId={selectedId} onSelect={selectPortfolio} />
        {portfolio.portfolio_type === 'CURRENT' && portfolio.holdings.length > 0 && (
          <div className={styles.currencyControl} role="group" aria-label="Dashboard value currency">
            {(['USD', 'THB'] as PortfolioCurrency[]).map(currency => (
              <button type="button" key={currency} className={valuationCurrency === currency ? styles.activeCurrency : ''} aria-pressed={valuationCurrency === currency} onClick={() => setValuationCurrency(currency)}>{currency}</button>
            ))}
          </div>
        )}
      </div>
      {Boolean(contextError) && <InlineErrorCard
        error={contextError}
        fallbackMessage={portfolio.portfolio_type === 'PLANNED' ? 'Unable to load the planned target allocation.' : 'Unable to load the current portfolio value.'}
        message={portfolio.portfolio_type === 'CURRENT'
          ? portfolioValuationErrorMessage(contextError)
          : undefined}
        stale={marketDataUnavailable || Boolean(valuation) || portfolio.portfolio_type === 'PLANNED'}
        staleMessage={marketDataUnavailable
          ? PORTFOLIO_MARKET_DATA_RECOVERY_MESSAGE
          : undefined}
        onRetry={() => setContextReloadKey(value => value + 1)}
        retryTitle={portfolio.portfolio_type === 'CURRENT' ? 'Retry Current Value' : 'Retry allocation'}
        compactAction={portfolio.portfolio_type === 'CURRENT'}
      />}
      {Boolean(reportError) && <InlineErrorCard error={reportError} fallbackMessage="Unable to load the latest report." resourceName="Latest report" stale onRetry={() => setReportReloadKey(value => value + 1)} retryTitle="Retry report" />}
      {!reportLoading && !reportError && !report && <div className={styles.reportNotice}><span><strong>This portfolio has not been analyzed.</strong> Risk and performance metrics will appear after you create an analysis.</span><button className="primary-btn" onClick={() => go(`analytics/${portfolio.id}`)}>Analyze Portfolio</button></div>}
      <DashboardKpiGrid portfolio={portfolio} valuation={valuation} plannedAllocation={plannedAllocation} contextLoading={contextLoading} contextFailed={Boolean(contextError)} report={report} reportLoading={reportLoading} reportFailed={Boolean(reportError)} />
      <div className="dashboard-primary-grid"><PortfolioPerformance key={report?.id ?? portfolio.id} portfolioId={portfolio.id} report={report} loading={reportLoading} failed={Boolean(reportError)} /><RiskDrivers portfolioId={report?.portfolio_id ?? portfolio.id} reportId={report?.id ?? null} drivers={report?.analysis.risk_drivers.entries ?? null} loading={reportLoading} failed={Boolean(reportError)} /></div>
      <div className="dashboard-bottom-grid"><PortfolioAllocation holdings={allocation} loading={contextLoading} title={portfolio.portfolio_type === 'PLANNED' ? 'Planned Target Allocation' : portfolio.portfolio_type === 'CURRENT' ? 'Current Portfolio Allocation' : 'Saved Portfolio Allocation'} /><AiInsight portfolioId={portfolio.id} report={report} /><PortfolioAnalysisCard portfolioId={portfolio.id} report={report} loading={reportLoading} failed={Boolean(reportError)} /></div>
    </>}
  </div>;
}
