import type { ReportSummary } from '../../../types/report';
import { Icon } from '../../../components/ui/Icon';
import { RiskPill } from '../../../components/ui/RiskPill';

interface ReportTableProps {
  reports: ReportSummary[];
  onDownload: (report: ReportSummary) => void;
  onDelete: (reportId: number) => void;
  onOpen: (report: ReportSummary) => void;
  onResetFilters: () => void;
}

function reportIcon(report: ReportSummary) {
  return report.type === 'Simulation'
    ? 'simulations'
    : report.type === 'Comparison'
      ? 'analytics'
      : 'reports';
}

export function ReportTable({
  reports,
  onDownload,
  onDelete,
  onOpen,
  onResetFilters,
}: ReportTableProps) {
  if (!reports.length) {
    return (
      <div className="reports-empty-state">
        <span><Icon name="reports" size={28} /></span>
        <h3>No reports found</h3>
        <p>Try changing your search or report-type filter.</p>
        <button className="secondary-btn" onClick={onResetFilters}>Reset Filters</button>
      </div>
    );
  }

  return (
    <div className="reports-table-wrap" role="region" aria-label="Saved reports" tabIndex={0}>
      <table className="reports-table">
        <thead>
          <tr>
            <th>Report</th><th>Portfolio</th><th>Type</th><th>Created</th><th>Risk Score</th><th aria-label="Actions" />
          </tr>
        </thead>
        <tbody>
          {reports.map(report => (
            <tr key={report.id}>
              <td>
                <div className={`report-name-cell ${report.type.toLowerCase()}`}>
                  <span><Icon name={reportIcon(report)} size={18} /></span>
                  <div>
                    {report.type === 'Analysis'
                      ? <button className="report-open-button" onClick={() => onOpen(report)}>{report.name}</button>
                      : <strong>{report.name}</strong>}
                    <small>{report.type === 'Analysis' ? 'Open saved analysis snapshot' : 'Educational portfolio risk report'}</small>
                  </div>
                </div>
              </td>
              <td>
                <div className="report-portfolio-cell">
                  <span>{report.portfolio.slice(0, 2).toUpperCase()}</span>
                  <strong>{report.portfolio}</strong>
                </div>
              </td>
              <td><span className={`report-type-badge ${report.type.toLowerCase()}`}>{report.type}</span></td>
              <td><div className="report-date-cell"><Icon name="calendar" size={15} /><span>{report.date}</span></div></td>
              <td>
                {report.riskScore
                  ? <div className="report-risk-score"><strong>{report.riskScore}</strong><RiskPill score={report.riskScore} /></div>
                  : <span className="not-applicable">Not applicable</span>}
              </td>
              <td>
                <div className="report-row-actions">
                  <button onClick={() => onDownload(report)} aria-label={`Download ${report.name}`} title="Download report"><span>↓</span></button>
                  <button className="delete" onClick={() => onDelete(report.id)} aria-label={`Delete ${report.name}`} title="Delete report">×</button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
