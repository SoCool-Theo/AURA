import { useEffect, useRef, useState } from 'react';
import {
  deletePortfolioReport,
  getPortfolioReport,
} from '../../api/reportsApi';
import { go } from '../../app/routes';
import { InlineErrorCard, ScreenErrorState } from '../../components/ui/ApiErrorState';
import { Icon } from '../../components/ui/Icon';
import { ConfirmationDialog } from '../../components/ui/ConfirmationDialog';
import {
  isPortfolioReportV2,
  isPortfolioReportV3,
  type PortfolioReportResponse,
} from '../../types/report';
import { formatReportTimestamp } from '../analytics/analyticsUi';
import { AnalysisResults } from '../analytics/components/AnalysisResults';
import styles from './ReportDetailPage.module.css';

interface ReportDetailPageProps {
  portfolioId: string;
  reportId: string;
  focusAssetSection?: boolean;
  focusRiskDrivers?: boolean;
}

export function ReportDetailPage({ portfolioId, reportId, focusAssetSection = false, focusRiskDrivers = false }: ReportDetailPageProps) {
  const [report, setReport] = useState<PortfolioReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [actionError, setActionError] = useState<unknown>(null);
  const [deleting, setDeleting] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const deletingRef = useRef(false);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setActionError(null);
    setReport(null);

    void getPortfolioReport(portfolioId, reportId, { signal: controller.signal })
      .then(setReport)
      .catch(requestError => {
        if (!controller.signal.aborted) setError(requestError);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [portfolioId, reportId, reloadKey]);

  useEffect(() => {
    if (!report || loading || error || (!focusAssetSection && !focusRiskDrivers)) return;
    const frame = window.requestAnimationFrame(() => {
      const section = document.getElementById(focusRiskDrivers ? 'risk-drivers' : 'per-asset-analysis');
      section?.scrollIntoView({ block: 'start' });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [focusAssetSection, focusRiskDrivers, report, loading, error]);

  async function remove() {
    if (deletingRef.current || !report) return;
    deletingRef.current = true;
    setDeleting(true);
    setActionError(null);
    try {
      await deletePortfolioReport(portfolioId, reportId);
      go('reports');
    } catch (requestError) {
      setActionError(requestError);
      deletingRef.current = false;
      setDeleting(false);
    }
  }

  if (loading) {
    return <div className={styles.state} role="status"><span className={styles.spinner} /><h2>Loading report</h2><p>Retrieving the immutable saved analysis snapshot.</p></div>;
  }

  if (error || !report) return <ScreenErrorState error={error ?? 'Report not found.'} fallbackMessage="Unable to retrieve this report." resourceName="Report" onRetry={() => setReloadKey(key => key + 1)} onBack={() => go('reports')} backTitle="Back to Reports" />;

  const reportType = isPortfolioReportV3(report)
    ? 'Planned Portfolio'
    : isPortfolioReportV2(report)
      ? 'Current Portfolio'
      : 'Legacy Portfolio';

  return (
    <div className={`page ${styles.page}`}>
      <button className={styles.backLink} onClick={() => go('reports')}>← Reports <span>/</span> Saved Analysis</button>
      {Boolean(actionError) && <InlineErrorCard error={actionError} fallbackMessage="Unable to delete report." />}
      <header className={styles.header}>
        <div>
          <div className={styles.titleRow}><h1>{report.analysis.portfolio_name} Analysis</h1><span>{reportType}</span><span>Immutable Snapshot</span></div>
          <p>Created {formatReportTimestamp(report.created_at)}<i>•</i>Report {report.id}</p>
        </div>
        <div className={styles.headerActions} aria-label="Report actions">
          <button
            className={styles.deleteButton}
            onClick={() => { setActionError(null); setDeleteOpen(true); }}
            disabled={deleting}
          >
            {deleting ? 'Deleting…' : 'Delete Report'}
          </button>
          <button className="primary-btn" onClick={() => go(`analytics/${report.portfolio_id}`)}>Run New Analysis</button>
        </div>
      </header>

      <AnalysisResults report={report} />

      <section className={`card ${styles.assistantCard}`}>
        <div>
          <small>NEED HELP UNDERSTANDING THE RESULTS?</small>
          <h2>Ask Aura about this saved report</h2>
          <p>Aura can explain this {isPortfolioReportV3(report) ? 'planned allocation' : 'portfolio'} using the exact snapshot shown above.</p>
        </div>
        <button className="primary-btn" onClick={() => go(`assistant/${report.portfolio_id}/report/${report.id}`)}><Icon name="assistant" size={17} /> Ask Aura</button>
      </section>
      {deleteOpen && <ConfirmationDialog
        title="Delete report?"
        description="This permanently removes the saved analysis snapshot and cannot be undone."
        subjectLabel="Saved report"
        subject={`${report.analysis.portfolio_name} · ${report.id}`}
        confirmLabel="Delete Report"
        busy={deleting}
        error={actionError}
        onCancel={() => { if (!deleting) { setDeleteOpen(false); setActionError(null); } }}
        onConfirm={() => void remove()}
      />}
    </div>
  );
}
