import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';
import type { PortfolioReportHistoryItem } from '../../../types/report';

interface ReportSummaryProps {
  reports: PortfolioReportHistoryItem[];
  portfolioCount: number;
}

export function ReportSummary({ reports, portfolioCount }: ReportSummaryProps) {
  const portfoliosWithReports = new Set(reports.map(report => report.portfolio_id)).size;

  return (
    <div className="report-summary-grid">
      <Card className="report-summary-card purple">
        <span><Icon name="reports" size={19} /></span>
        <div><small>Total Reports</small><strong>{reports.length}</strong><p>Saved in your library</p></div>
      </Card>
      <Card className="report-summary-card blue">
        <span><Icon name="analysis" size={19} /></span>
        <div><small>Analysis Snapshots</small><strong>{reports.length}</strong><p>Immutable backend reports</p></div>
      </Card>
      <Card className="report-summary-card amber">
        <span><Icon name="wallet" size={19} /></span>
        <div><small>Portfolios Checked</small><strong>{portfolioCount}</strong><p>Owned portfolios queried</p></div>
      </Card>
      <Card className="report-summary-card green">
        <span><Icon name="reports" size={19} /></span>
        <div><small>With Reports</small><strong>{portfoliosWithReports}</strong><p>Portfolios with history</p></div>
      </Card>
    </div>
  );
}
