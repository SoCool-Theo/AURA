import { Card } from '../ui/Card';
import { Icon } from '../ui/Icon';

interface PortfolioMetricProps {
  label: string;
  value: string;
  detail: string;
  icon: string;
  tone: string;
}

export function PortfolioMetric({ label, value, detail, icon, tone }: PortfolioMetricProps) {
  return (
    <Card className={`detail-metric-card ${tone}`}>
      <span className="detail-metric-icon"><Icon name={icon} size={20} /></span>
      <div>
        <small>{label}</small>
        <strong>{value}</strong>
        <span>{detail}</span>
      </div>
    </Card>
  );
}
