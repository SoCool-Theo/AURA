import { Icon } from '../../../components/ui/Icon';
import type { PortfolioReportHistoryItem } from '../../../types/report';
import { formatReportTimestamp } from '../../analytics/analyticsUi';
import styles from '../ReportsPage.module.css';

interface ReportTableProps {
  reports: PortfolioReportHistoryItem[];
  totalReportCount: number;
  onOpen: (report: PortfolioReportHistoryItem) => void;
  onCreateAnalysis: () => void;
  onResetFilters: () => void;
  onDelete: (report: PortfolioReportHistoryItem) => void;
  deletingReportIds: ReadonlySet<string>;
}

export function ReportTable({
  reports,
  totalReportCount,
  onOpen,
  onCreateAnalysis,
  onResetFilters,
  onDelete,
  deletingReportIds,
}: ReportTableProps) {
  if (!reports.length) {
    const historyIsEmpty = totalReportCount === 0;
    return (
      <div className="reports-empty-state">
        <span><Icon name="reports" size={28} /></span>
        <h3>{historyIsEmpty ? 'No saved analysis reports' : 'No reports match these filters'}</h3>
        <p>{historyIsEmpty ? 'Run a portfolio analysis to create the first immutable report snapshot.' : 'Try changing the portfolio filter or search text.'}</p>
        <button className={historyIsEmpty ? 'primary-btn' : 'secondary-btn'} onClick={historyIsEmpty ? onCreateAnalysis : onResetFilters}>{historyIsEmpty ? 'Create Analysis' : 'Reset Filters'}</button>
      </div>
    );
  }

  return (
    <div className="reports-table-wrap" role="region" aria-label="Saved reports" tabIndex={0}>
      <table className="reports-table">
        <thead>
          <tr>
            <th>Report</th><th>Portfolio</th><th>Requested Period</th><th>Created</th><th aria-label="Actions" />
          </tr>
        </thead>
        <tbody>
          {reports.map(report => {
            const deleting = deletingReportIds.has(report.id);
            return <tr key={report.id}>
              <td>
                <div className="report-name-cell analysis">
                  <span><Icon name="reports" size={18} /></span>
                  <div>
                    <button className="report-open-button" onClick={() => onOpen(report)}>Portfolio Analysis</button>
                    <small>ID {report.id}</small>
                  </div>
                </div>
              </td>
              <td>
                <div className="report-portfolio-cell">
                  <span>{report.portfolio_name.slice(0, 2).toUpperCase()}</span>
                  <strong>{report.portfolio_name}</strong>
                </div>
              </td>
              <td><span className="report-type-badge analysis">{report.start_date} → {report.end_date}</span></td>
              <td><div className="report-date-cell"><Icon name="calendar" size={15} /><span>{formatReportTimestamp(report.created_at)}</span></div></td>
              <td>
                <div className="report-row-actions">
                  <button onClick={() => onOpen(report)} aria-label={`Open report ${report.id}`} title="Open saved snapshot">→</button>
                  <button
                    className={`${styles.deleteAction} delete`}
                    onClick={() => onDelete(report)}
                    disabled={deleting}
                    aria-label={deleting ? `Deleting report ${report.id}` : `Delete report ${report.id}`}
                    title={deleting ? 'Deleting saved report' : 'Delete saved report'}
                  >
                    {deleting ? 'Deleting…' : 'Delete'}
                  </button>
                </div>
              </td>
            </tr>
          })}
        </tbody>
      </table>
    </div>
  );
}
