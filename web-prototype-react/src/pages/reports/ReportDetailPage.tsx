import { useEffect, useState } from 'react';
import { getPortfolioReport } from '../../api/reportsApi';
import { go } from '../../app/routes';
import { Icon } from '../../components/ui/Icon';
import type { PortfolioReportResponse } from '../../types/report';
import { analysisErrorMessage, formatReportTimestamp } from '../analytics/analyticsUi';
import { AnalysisResults } from '../analytics/components/AnalysisResults';
import styles from './ReportDetailPage.module.css';

interface ReportDetailPageProps {
  portfolioId: string;
  reportId: string;
}

export function ReportDetailPage({ portfolioId, reportId }: ReportDetailPageProps) {
  const [report, setReport] = useState<PortfolioReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setReport(null);

    void getPortfolioReport(portfolioId, reportId, { signal: controller.signal })
      .then(setReport)
      .catch(requestError => {
        if (!controller.signal.aborted) setError(analysisErrorMessage(requestError, 'Unable to retrieve report.'));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [portfolioId, reportId, reloadKey]);

  if (loading) {
    return <div className={styles.state} role="status"><span className={styles.spinner} /><h2>Loading report</h2><p>Retrieving the immutable saved analysis snapshot.</p></div>;
  }

  if (error || !report) {
    return (
      <div className={styles.state} role="alert">
        <span className={styles.stateIcon}><Icon name="reports" size={29} /></span>
        <h2>Report unavailable</h2>
        <p>{error || 'Report not found'}</p>
        <div><button className="primary-btn" onClick={() => setReloadKey(key => key + 1)}>Try Again</button><button className="secondary-btn" onClick={() => go('reports')}>Back to Reports</button></div>
      </div>
    );
  }

  return (
    <div className={`page ${styles.page}`}>
      <button className={styles.backLink} onClick={() => go('reports')}>← Reports <span>/</span> Saved Analysis</button>
      <header className={styles.header}>
        <div>
          <div className={styles.titleRow}><h1>{report.analysis.portfolio_name} Analysis</h1><span>Immutable Snapshot</span></div>
          <p>Created {formatReportTimestamp(report.created_at)}<i>•</i>Report {report.id}</p>
        </div>
        <div className={styles.headerActions} aria-label="Report actions">
          <button className="secondary-btn" onClick={() => go(`analytics/${report.portfolio_id}`)}>Analyze Current Portfolio</button>
        </div>
      </header>

      <AnalysisResults analysis={report.analysis} />
    </div>
  );
}
