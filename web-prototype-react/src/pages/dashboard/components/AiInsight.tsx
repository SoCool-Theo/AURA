import type { PortfolioReportResponse } from '../../../types/report';
import { go } from '../../../app/routes';
import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';
import styles from '../DashboardIntegration.module.css';

export function AiInsight({ portfolioId, report }: { portfolioId: string; report: PortfolioReportResponse | null }) {
  const openAssistant = () => go(report
    ? `assistant/${report.portfolio_id}/report/${report.id}`
    : `assistant/${portfolioId}`);

  return <Card className="dashboard-insight-card">
    <div className="dashboard-card-header"><div className="dashboard-card-title"><span className="title-icon"><Icon name="spark" size={21} /></span><h2>AI Explanation</h2></div></div>
    <div className={styles.insightBody}>
      <p>{report ? 'Ask Aura to explain the latest saved risk results in clear, educational language.' : 'Ask Aura about this portfolio, or create an analysis first for saved risk results.'}</p>
      <div className={styles.insightContext}>
        <span>{report ? 'LATEST SAVED ANALYSIS' : 'SELECTED PORTFOLIO'}</span>
        <strong>{report?.analysis.portfolio_name ?? 'Portfolio context'}</strong>
      </div>
    </div>
    <button type="button" className={`primary-btn ${styles.insightButton}`} onClick={openAssistant}><Icon name="spark" size={17} /> Ask Aura</button>
  </Card>;
}
