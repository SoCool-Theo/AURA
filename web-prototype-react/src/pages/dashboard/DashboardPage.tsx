import { useEffect, useState } from 'react';
import { getPortfolio, listPortfolios } from '../../api/portfoliosApi';
import { getPortfolioReport, listPortfolioReports } from '../../api/reportsApi';
import { useAuth } from '../../auth/useAuth';
import { go } from '../../app/routes';
import { Card } from '../../components/ui/Card';
import type { PortfolioResponse, PortfolioSummaryResponse } from '../../types/portfolio';
import type { PortfolioReportResponse } from '../../types/report';
import styles from './DashboardIntegration.module.css';
import { AiInsight } from './components/AiInsight';
import { DashboardHeader } from './components/DashboardHeader';
import { DashboardKpiGrid } from './components/DashboardKpiGrid';
import { PortfolioAllocation } from './components/PortfolioAllocation';
import { PortfolioAnalysisCard } from './components/PortfolioAnalysisCard';
import { PortfolioPerformance } from './components/PortfolioPerformance';
import { RiskDrivers } from './components/RiskDrivers';
import { dashboardErrorMessage } from './dashboardUi';

export function DashboardPage() {
  const { user } = useAuth();
  const [portfolios, setPortfolios] = useState<PortfolioSummaryResponse[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);
  const [report, setReport] = useState<PortfolioReportResponse | null>(null);
  const [listLoading, setListLoading] = useState(true);
  const [portfolioLoading, setPortfolioLoading] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [portfolioError, setPortfolioError] = useState<string | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [reportReloadKey, setReportReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController(); setListLoading(true); setListError(null); setPortfolios([]); setSelectedId('');
    void listPortfolios({ signal: controller.signal }).then(response => { setPortfolios(response.portfolios); setSelectedId(response.portfolios[0]?.id ?? ''); }).catch(error => { if (!controller.signal.aborted) setListError(dashboardErrorMessage(error, 'Unable to load portfolios.')); }).finally(() => { if (!controller.signal.aborted) setListLoading(false); });
    return () => controller.abort();
  }, [reloadKey]);

  useEffect(() => {
    setPortfolio(null); setReport(null); setPortfolioError(null); setReportError(null);
    if (!selectedId) { setPortfolioLoading(false); setReportLoading(false); return; }
    const controller = new AbortController(); setPortfolioLoading(true); setReportLoading(true);
    void getPortfolio(selectedId, { signal: controller.signal }).then(setPortfolio).catch(error => { if (!controller.signal.aborted) setPortfolioError(dashboardErrorMessage(error, 'Unable to load the selected portfolio.')); }).finally(() => { if (!controller.signal.aborted) setPortfolioLoading(false); });
    void listPortfolioReports(selectedId, { signal: controller.signal }).then(async response => {
      const latest = response.reports[0];
      if (!latest) return;
      const detail = await getPortfolioReport(selectedId, latest.id, { signal: controller.signal });
      if (!controller.signal.aborted) setReport(detail);
    }).catch(error => { if (!controller.signal.aborted) setReportError(dashboardErrorMessage(error, 'Unable to load the latest report.')); }).finally(() => { if (!controller.signal.aborted) setReportLoading(false); });
    return () => controller.abort();
  }, [selectedId, reportReloadKey]);

  function selectPortfolio(nextId: string) {
    if (nextId === selectedId) return;
    setPortfolio(null); setReport(null); setPortfolioError(null); setReportError(null);
    setPortfolioLoading(true); setReportLoading(true); setSelectedId(nextId);
  }

  const firstName = user?.email.split('@')[0] || 'Investor';
  if (listLoading) return <Card className={styles.state}><h2>Loading Dashboard</h2><p role="status">Retrieving your real portfolio list.</p></Card>;
  if (listError) return <div role="alert"><Card className={styles.state}><h2>Dashboard unavailable</h2><p>{listError}</p><button className="primary-btn" onClick={() => setReloadKey(value => value + 1)}>Try Again</button></Card></div>;
  if (!portfolios.length) return <Card className={styles.state}><h2>No portfolios yet</h2><p>Create a saved symbol-and-weight portfolio to begin using Aura’s Dashboard.</p><button className="primary-btn" onClick={() => go('create')}>Create Portfolio</button></Card>;

  return <div className="page dashboard-page">
    <DashboardHeader firstName={firstName} portfolios={portfolios} selectedId={selectedId} report={report} onSelectPortfolio={selectPortfolio} />
    {portfolioError && <p className={styles.error} role="alert">{portfolioError}</p>}
    {portfolioLoading && <Card className={styles.state}><h2>Loading selected portfolio</h2><p role="status">Clearing prior metrics and retrieving the selected portfolio.</p></Card>}
    {!portfolioLoading && !portfolio && !portfolioError && <Card className={styles.state}><h2>Portfolio unavailable</h2><p>The selected portfolio could not be displayed.</p></Card>}
    {portfolio && <>
      {reportError && <div className={styles.reportNotice} role="alert"><span><strong>Report metrics unavailable.</strong> {reportError}</span><button className="secondary-btn" onClick={() => setReportReloadKey(value => value + 1)}>Retry Report</button></div>}
      {!reportLoading && !reportError && !report && <div className={styles.reportNotice}><span><strong>This portfolio has not been analyzed.</strong> Report-backed metrics remain N/A until you create an analysis.</span><button className="primary-btn" onClick={() => go(`analytics/${portfolio.id}`)}>Analyze Portfolio</button></div>}
      <DashboardKpiGrid portfolio={portfolio} report={report} reportLoading={reportLoading} reportFailed={Boolean(reportError)} />
      <div className="dashboard-primary-grid"><PortfolioPerformance portfolioId={portfolio.id} report={report} loading={reportLoading} failed={Boolean(reportError)} /><RiskDrivers portfolioId={portfolio.id} drivers={report?.analysis.risk_drivers.entries ?? null} loading={reportLoading} failed={Boolean(reportError)} /></div>
      <div className="dashboard-bottom-grid"><PortfolioAllocation holdings={portfolio.holdings} /><AiInsight /><PortfolioAnalysisCard portfolioId={portfolio.id} report={report} loading={reportLoading} failed={Boolean(reportError)} /></div>
    </>}
  </div>;
}
