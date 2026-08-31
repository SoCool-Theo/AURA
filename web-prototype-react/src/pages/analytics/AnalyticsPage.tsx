import { useEffect, useState } from 'react';
import { createPortfolioReport } from '../../api/reportsApi';
import { listPortfolios } from '../../api/portfoliosApi';
import { go } from '../../app/routes';
import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import { AuraSelect } from '../../components/ui/AuraSelect';
import type { AuraSelectOption } from '../../components/ui/AuraSelect';
import type { PortfolioSummaryResponse } from '../../types/portfolio';
import type { PortfolioReportResponse } from '../../types/report';
import { analysisErrorMessage, formatReportTimestamp } from './analyticsUi';
import styles from './AnalyticsIntegration.module.css';
import { AnalysisResults } from './components/AnalysisResults';

interface AnalyticsPageProps {
  portfolioId?: string;
}

function localIsoDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function defaultPeriod() {
  const end = new Date();
  const start = new Date(end);
  start.setFullYear(start.getFullYear() - 1);
  return { start: localIsoDate(start), end: localIsoDate(end) };
}

export function AnalyticsPage({ portfolioId }: AnalyticsPageProps) {
  const initialPeriod = defaultPeriod();
  const [portfolios, setPortfolios] = useState<PortfolioSummaryResponse[]>([]);
  const [selectedPortfolioId, setSelectedPortfolioId] = useState('');
  const [startDate, setStartDate] = useState(initialPeriod.start);
  const [endDate, setEndDate] = useState(initialPeriod.end);
  const [report, setReport] = useState<PortfolioReportResponse | null>(null);
  const [loadingPortfolios, setLoadingPortfolios] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoadingPortfolios(true);
    setError(null);
    void listPortfolios({ signal: controller.signal })
      .then(response => {
        setPortfolios(response.portfolios);
        const requestedPortfolioExists = portfolioId
          ? response.portfolios.some(item => item.id === portfolioId)
          : false;
        if (portfolioId && !requestedPortfolioExists) setError('Portfolio not found');
        setSelectedPortfolioId(current => {
          if (portfolioId) {
            return requestedPortfolioExists ? portfolioId : '';
          }
          if (current && response.portfolios.some(item => item.id === current)) return current;
          return response.portfolios[0]?.id ?? '';
        });
      })
      .catch(requestError => {
        if (!controller.signal.aborted) setError(analysisErrorMessage(requestError, 'Unable to load portfolios.'));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingPortfolios(false);
      });
    return () => controller.abort();
  }, [portfolioId, reloadKey]);

  async function analyze() {
    if (analyzing) return;
    if (!selectedPortfolioId || !startDate || !endDate) {
      setError('Choose a portfolio, start date, and end date.');
      return;
    }
    if (startDate > endDate) {
      setError('Start date must be on or before end date.');
      return;
    }

    setAnalyzing(true);
    setError(null);
    setReport(null);
    try {
      setReport(await createPortfolioReport(selectedPortfolioId, {
        start_date: startDate,
        end_date: endDate,
      }));
    } catch (requestError) {
      setError(analysisErrorMessage(requestError, 'Unable to analyze this portfolio.'));
    } finally {
      setAnalyzing(false);
    }
  }

  const selectedPortfolio = portfolios.find(item => item.id === selectedPortfolioId);
  const portfolioOptions: AuraSelectOption<string>[] = [
    {
      value: '',
      label: loadingPortfolios
        ? 'Loading portfolios…'
        : portfolios.length
          ? 'Select a portfolio'
          : 'No portfolios available',
      description: 'Choose an owned saved portfolio',
      icon: 'wallet',
      tone: 'neutral',
      disabled: true,
    },
    ...portfolios.map(portfolio => ({
      value: portfolio.id,
      label: portfolio.name,
      description: 'Saved portfolio',
      icon: 'wallet',
      tone: 'teal' as const,
    })),
  ];

  function selectPortfolio(nextPortfolioId: string) {
    setSelectedPortfolioId(nextPortfolioId);
    setReport(null);
    setError(null);
  }

  return (
    <div className="page analytics-page">
      <header className="analytics-header">
        <div><h1>Portfolio Analysis</h1><p>Run Aura’s backend analysis and save an immutable report snapshot.</p></div>
        <div>
          <button className="secondary-btn" onClick={() => go('reports')}><Icon name="reports" size={17} /> Report History</button>
          {selectedPortfolio && <button className="secondary-btn" onClick={() => go(`portfolio/${selectedPortfolio.id}`)}>View Portfolio</button>}
        </div>
      </header>

      <Card className={styles.controls}>
        <div className={styles.controlsHeading}>
          <div><h2>Analysis period</h2><p>The exact requested calendar dates are sent to the reporting endpoint without trading-day adjustment.</p></div>
          <span className={styles.badge}>Creates one saved report</span>
        </div>
        <div className={styles.controlGrid}>
          <div className={styles.analysisFields}>
            <div className={styles.field}>
              <span>Portfolio</span>
              <AuraSelect
                className={styles.portfolioSelect}
                ariaLabel="Select portfolio for analysis"
                value={selectedPortfolioId}
                options={portfolioOptions}
                onChange={selectPortfolio}
                disabled={loadingPortfolios || analyzing}
              />
            </div>
            <label className={styles.field}>Start Date<input type="date" value={startDate} onChange={event => { setStartDate(event.target.value); setReport(null); setError(null); }} disabled={analyzing} /></label>
            <label className={styles.field}>End Date<input type="date" value={endDate} onChange={event => { setEndDate(event.target.value); setReport(null); setError(null); }} disabled={analyzing} /></label>
          </div>
          <button className="primary-btn" onClick={() => void analyze()} disabled={loadingPortfolios || analyzing || !selectedPortfolioId}>{analyzing ? 'Analyzing…' : 'Analyze Portfolio'}</button>
        </div>
      </Card>

      {error && <p className={styles.error} role="alert">{error}</p>}
      {loadingPortfolios && <Card className={styles.stateCard}><h2>Loading portfolios</h2><p role="status">Retrieving your real portfolio list.</p></Card>}
      {!loadingPortfolios && error && !portfolios.length && <Card className={styles.stateCard}><h2>Portfolios unavailable</h2><p>Analysis cannot begin until the portfolio list loads.</p><button className="primary-btn" onClick={() => setReloadKey(key => key + 1)}>Try again</button></Card>}
      {!loadingPortfolios && !error && !portfolios.length && <Card className={styles.stateCard}><h2>No portfolios to analyze</h2><p>Create a portfolio with an ordered allocation before running analysis.</p><button className="primary-btn" onClick={() => go('create')}>Create Portfolio</button></Card>}
      {analyzing && <Card className={styles.stateCard}><h2>Running portfolio analysis</h2><p role="status">Aura is calculating the requested period and saving the report snapshot.</p></Card>}
      {report && !analyzing && <>
        <div className={styles.savedBar}>
          <span><strong>Report saved.</strong> Created {formatReportTimestamp(report.created_at)} with ID {report.id}.</span>
          <div><button className="secondary-btn" onClick={() => go(`reports/${report.portfolio_id}/${report.id}`)}>Open Saved Report</button><button className="secondary-btn" onClick={() => go('reports')}>All Reports</button></div>
        </div>
        <AnalysisResults analysis={report.analysis} />
      </>}
    </div>
  );
}
