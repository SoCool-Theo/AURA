import { useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import type { ReportSummary as ReportSummaryType } from '../../types/report';
import { go } from '../../app/routes';
import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import { slug } from '../../utils/uiCalculations';
import { ReportFilters } from './components/ReportFilters';
import type { ReportTypeFilter } from './components/ReportFilters';
import { ReportSummary } from './components/ReportSummary';
import { ReportTable } from './components/ReportTable';

interface ReportsPageProps {
  reports: ReportSummaryType[];
  setReports: Dispatch<SetStateAction<ReportSummaryType[]>>;
}

export function ReportsPage({ reports, setReports }: ReportsPageProps) {
  const [query, setQuery] = useState('');
  const [type, setType] = useState<ReportTypeFilter>('All Types');
  const visible = reports.filter(report => (
    (type === 'All Types' || report.type === type)
    && report.name.toLowerCase().includes(query.toLowerCase())
  ));

  function resetFilters() {
    setQuery('');
    setType('All Types');
  }

  function download(report: ReportSummaryType) {
    const body = `AURA REPORT\n\n${report.name}\nPortfolio: ${report.portfolio}\nType: ${report.type}\nDate: ${report.date}\nRisk Score: ${report.riskScore ?? 'N/A'}\n\nEducational portfolio risk report prototype.`;
    const blob = new Blob([body], { type: 'text/plain' });
    const anchor = document.createElement('a');
    anchor.href = URL.createObjectURL(blob);
    anchor.download = `${slug(report.name)}.txt`;
    anchor.click();
    URL.revokeObjectURL(anchor.href);
  }

  function remove(reportId: number) {
    setReports(previous => previous.filter(report => report.id !== reportId));
  }

  function openReport(report: ReportSummaryType) {
    if (report.type !== 'Analysis') return;
    const legacyPortfolioIds: Record<string, string> = {
      'Tech Portfolio': 'tech',
      'Balanced Portfolio': 'balanced',
      'Retirement Fund': 'retirement',
      'Long Term Growth': 'growth',
    };
    const portfolioId = report.portfolioId || legacyPortfolioIds[report.portfolio] || 'unknown';
    go(`reports/${portfolioId}/${report.id}`);
  }

  return (
    <div className="page reports-page">
      <header className="reports-header">
        <div>
          <span>PORTFOLIO DOCUMENTS</span>
          <h1>Reports</h1>
          <p>Review, filter, and download your saved portfolio analyses and simulations.</p>
        </div>
        <button className="primary-btn" onClick={() => go('analytics')}>
          <Icon name="analysis" size={17} /> Create New Analysis
        </button>
      </header>

      <ReportSummary reports={reports} />

      <Card className="reports-library-card">
        <div className="reports-library-heading">
          <div><h2>Report Library</h2><p>All generated reports are stored here for future reference.</p></div>
          <span>{visible.length} {visible.length === 1 ? 'report' : 'reports'}</span>
        </div>
        <ReportFilters
          query={query}
          type={type}
          onQueryChange={setQuery}
          onTypeChange={setType}
          onReset={resetFilters}
        />
        <ReportTable
          reports={visible}
          onDownload={download}
          onDelete={remove}
          onOpen={openReport}
          onResetFilters={resetFilters}
        />
        <div className="table-footer">
          <span>Showing <strong>{visible.length}</strong> of <strong>{reports.length}</strong> reports</span>
          <div>
            <button aria-label="Previous page">‹</button>
            <button className="active">1</button>
            <button aria-label="Next page">›</button>
          </div>
        </div>
      </Card>
      <div className="reports-education-note">
        <Icon name="shield" size={16} />
        <p>Reports summarize calculated and historical portfolio risk for educational use. They are not investment recommendations.</p>
      </div>
    </div>
  );
}
