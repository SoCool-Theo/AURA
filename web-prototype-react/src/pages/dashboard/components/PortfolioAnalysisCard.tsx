import { go } from '../../../app/routes';
import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';

interface PortfolioAnalysisCardProps {
  portfolioId: string;
  riskScore: number;
  riskLabel: string;
}

export function PortfolioAnalysisCard({
  portfolioId,
  riskScore,
  riskLabel,
}: PortfolioAnalysisCardProps) {
  return (
    <Card className="dashboard-analysis-card">
      <div className="dashboard-card-header">
        <div className="dashboard-card-title">
          <span className="title-icon"><Icon name="analysis" size={22} /></span>
          <h2>Portfolio Analysis</h2>
        </div>
      </div>
      <div className="analysis-status">
        <p>Last analyzed: May 11, 2026</p>
        <p>Risk score: <strong>{riskScore}</strong><span>•</span><b>{riskLabel}</b></p>
      </div>
      <div className="analysis-card-actions">
        <button className="primary-btn" onClick={() => go(`analytics/${portfolioId}`)}>
          View Analysis <span>→</span>
        </button>
        <button className="secondary-btn" onClick={() => go(`analytics/${portfolioId}`)}>
          Re-analyze <span>↻</span>
        </button>
      </div>
    </Card>
  );
}
