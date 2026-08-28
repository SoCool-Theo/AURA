import type { ReportSummary as ReportSummaryType } from '../../../types/report';
import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';

interface ReportSummaryProps {
  reports: ReportSummaryType[];
}

export function ReportSummary({ reports }: ReportSummaryProps) {
  const reportCounts = {
    analysis: reports.filter(report => report.type === 'Analysis').length,
    simulation: reports.filter(report => report.type === 'Simulation').length,
    comparison: reports.filter(report => report.type === 'Comparison').length,
  };

  return (
    <div className="report-summary-grid">
      <Card className="report-summary-card purple">
        <span><Icon name="reports" size={19} /></span>
        <div><small>Total Reports</small><strong>{reports.length}</strong><p>Saved in your library</p></div>
      </Card>
      <Card className="report-summary-card blue">
        <span><Icon name="analysis" size={19} /></span>
        <div><small>Portfolio Analyses</small><strong>{reportCounts.analysis}</strong><p>Risk analysis reports</p></div>
      </Card>
      <Card className="report-summary-card amber">
        <span><Icon name="simulations" size={19} /></span>
        <div><small>Simulations</small><strong>{reportCounts.simulation}</strong><p>Historical scenario results</p></div>
      </Card>
      <Card className="report-summary-card green">
        <span><Icon name="analytics" size={19} /></span>
        <div><small>Comparisons</small><strong>{reportCounts.comparison}</strong><p>Portfolio comparisons</p></div>
      </Card>
    </div>
  );
}
