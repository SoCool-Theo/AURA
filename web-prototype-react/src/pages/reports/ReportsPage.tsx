import { useEffect, useRef, useState } from 'react';
import { listPortfolios } from '../../api/portfoliosApi';
import {
  deletePortfolioReport,
  listPortfolioReports,
} from '../../api/reportsApi';
import { go } from '../../app/routes';
import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import type { PortfolioSummaryResponse } from '../../types/portfolio';
import type { PortfolioReportHistoryItem } from '../../types/report';
import { analysisErrorMessage } from '../analytics/analyticsUi';
import { ReportFilters } from './components/ReportFilters';
import { ReportSummary } from './components/ReportSummary';
import { ReportTable } from './components/ReportTable';
import styles from './ReportsPage.module.css';

export function ReportsPage() {
  const [reports, setReports] = useState<PortfolioReportHistoryItem[]>([]);
  const [portfolios, setPortfolios] = useState<PortfolioSummaryResponse[]>([]);
  const [query, setQuery] = useState('');
  const [portfolioId, setPortfolioId] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const deletingReportIdsRef = useRef(new Set<string>());
  const [deletingReportIds, setDeletingReportIds] = useState<Set<string>>(
    new Set(),
  );

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setActionError(null);
    setReports([]);

    void listPortfolios({ signal: controller.signal })
      .then(async response => {
        setPortfolios(response.portfolios);
        setPortfolioId(current => (
          !current || response.portfolios.some(portfolio => portfolio.id === current)
            ? current
            : ''
        ));
        const histories = await Promise.all(response.portfolios.map(async portfolio => ({
          portfolio,
          history: await listPortfolioReports(portfolio.id, { signal: controller.signal }),
        })));
        if (controller.signal.aborted) return;
        setReports(histories.flatMap(({ portfolio, history }) => (
          history.reports.map(report => ({ ...report, portfolio_name: portfolio.name }))
        )));
      })
      .catch(requestError => {
        if (!controller.signal.aborted) setError(analysisErrorMessage(requestError, 'Unable to load report history.'));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [reloadKey]);

  const normalizedQuery = query.trim().toLowerCase();
  const visible = reports.filter(report => (
    (!portfolioId || report.portfolio_id === portfolioId)
    && (!normalizedQuery
      || report.portfolio_name.toLowerCase().includes(normalizedQuery)
      || report.id.toLowerCase().includes(normalizedQuery))
  ));

  function resetFilters() {
    setQuery('');
    setPortfolioId('');
  }

  async function remove(report: PortfolioReportHistoryItem) {
    if (deletingReportIdsRef.current.has(report.id)) return;
    if (!confirm(
      `Delete the saved analysis report for ${report.portfolio_name}? This cannot be undone.`,
    )) return;

    deletingReportIdsRef.current.add(report.id);
    setDeletingReportIds(new Set(deletingReportIdsRef.current));
    setActionError(null);
    try {
      await deletePortfolioReport(report.portfolio_id, report.id);
      setReports(previous => previous.filter(item => item.id !== report.id));
    } catch (requestError) {
      setActionError(analysisErrorMessage(
        requestError,
        'Unable to delete report.',
      ));
    } finally {
      deletingReportIdsRef.current.delete(report.id);
      setDeletingReportIds(new Set(deletingReportIdsRef.current));
    }
  }

  return (
    <div className="page reports-page">
      <header className="reports-header">
        <div>
          <span>IMMUTABLE ANALYSIS SNAPSHOTS</span>
          <h1>Reports</h1>
          <p>Real report history composed from each owned portfolio’s reporting endpoint.</p>
        </div>
        <button className="primary-btn" onClick={() => go('analytics')}>
          <Icon name="analysis" size={17} /> Create New Analysis
        </button>
      </header>

      {actionError && (
        <p className={styles.actionError} role="alert">{actionError}</p>
      )}

      {!loading && !error && <ReportSummary reports={reports} portfolioCount={portfolios.length} />}

      <Card className="reports-library-card">
        <div className="reports-library-heading">
          <div><h2>Report Library</h2><p>Browse immutable analysis snapshots for each portfolio.</p></div>
          <span>{visible.length} {visible.length === 1 ? 'report' : 'reports'}</span>
        </div>

        {!loading && !error && <ReportFilters
          query={query}
          portfolioId={portfolioId}
          portfolios={portfolios}
          onQueryChange={setQuery}
          onPortfolioChange={setPortfolioId}
          onReset={resetFilters}
        />}

        {loading && <div className="reports-empty-state" role="status"><span><Icon name="reports" size={28} /></span><h3>Loading report history</h3><p>Retrieving owned portfolios and their saved reports.</p></div>}
        {error && <div className="reports-empty-state" role="alert"><span><Icon name="reports" size={28} /></span><h3>Report history unavailable</h3><p>{error}</p><button className="primary-btn" onClick={() => setReloadKey(key => key + 1)}>Try Again</button></div>}
        {!loading && !error && <ReportTable
          reports={visible}
          totalReportCount={reports.length}
          onOpen={report => go(`reports/${report.portfolio_id}/${report.id}`)}
          onCreateAnalysis={() => go('analytics')}
          onResetFilters={resetFilters}
          onDelete={report => void remove(report)}
          deletingReportIds={deletingReportIds}
        />}

        {!loading && !error && <div className="table-footer">
          <span>Showing <strong>{visible.length}</strong> of <strong>{reports.length}</strong> saved analysis reports</span>
          <span>Read-only history</span>
        </div>}
      </Card>
      <div className="reports-education-note">
        <Icon name="shield" size={16} />
        <p>Deletion permanently removes the saved report. Export, sharing, and download generation remain unavailable.</p>
      </div>
    </div>
  );
}
