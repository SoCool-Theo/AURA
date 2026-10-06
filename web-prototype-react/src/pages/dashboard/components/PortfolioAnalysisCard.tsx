import type { PortfolioReportResponse } from '../../../types/report';
import { go } from '../../../app/routes';
import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';
import { formatTimestamp } from '../dashboardUi';
import styles from '../DashboardIntegration.module.css';

export function PortfolioAnalysisCard({ portfolioId, report, loading, failed }: { portfolioId: string; report: PortfolioReportResponse | null; loading: boolean; failed: boolean }) {
  return <Card className="dashboard-analysis-card">
    <div className="dashboard-card-header"><div className="dashboard-card-title"><span className="title-icon"><Icon name="analytics" size={22} /></span><h2>Core Workflows</h2></div></div>
    <div className={styles.analysisMeta}>{loading ? <span role="status">Loading latest analysis…</span> : report ? <span>Latest report created <strong>{formatTimestamp(report.created_at)}</strong> for {report.analysis.start_date} through {report.analysis.end_date}.</span> : failed ? <span>Latest report context is currently unavailable.</span> : <span>This portfolio has not been analyzed yet. Create a report to populate report-backed Dashboard metrics.</span>}</div>
    <div className={styles.actions}>
      <button className="secondary-btn" onClick={() => go(`portfolio/${portfolioId}`)}>Open Portfolio</button>
      <button className="primary-btn" onClick={() => go(`analytics/${portfolioId}`)}>{report ? 'Analyze Again' : 'Analyze Portfolio'}</button>
      {report && <button className="secondary-btn" onClick={() => go(`reports/${portfolioId}/${report.id}`)}>View Latest Report</button>}
      <button type="button" className="secondary-btn" onClick={() => go(`forecasting/portfolio/${portfolioId}`)}>View 30-Day Outlook</button>
      <button className="secondary-btn" onClick={() => go('reports')}>View Reports</button>
      <button className="secondary-btn" onClick={() => go(`simulations/${portfolioId}`)}>Simulate</button>
    </div>
  </Card>;
}
