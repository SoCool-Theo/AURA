import { go } from '../../../app/routes';
import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';

interface AiInsightProps {
  riskScore: number;
  riskLabel: string;
}

export function AiInsight({ riskScore, riskLabel }: AiInsightProps) {
  return (
    <Card className="dashboard-insight-card">
      <div className="dashboard-card-header">
        <div className="dashboard-card-title">
          <span className="title-icon"><Icon name="spark" size={21} /></span>
          <h2>AI Insight</h2>
        </div>
      </div>
      <p>
        Your portfolio risk score is <strong>{riskScore} ({riskLabel})</strong>.
        {' '}Concentration in the largest holdings increases historical drawdown risk.
        {' '}Broader diversification may improve long-term resilience.
      </p>
      <button className="primary-btn insight-action" onClick={() => go('assistant')}>
        Ask Aura <span>→</span>
      </button>
    </Card>
  );
}
