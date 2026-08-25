import { lineA } from '../../../mocks/dashboard.mock';
import { pct } from '../../../utils/formatting';
import { LineChart } from '../../../components/charts/LineChart';
import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';

interface PortfolioPerformanceProps {
  annualizedReturn: number;
}

export function PortfolioPerformance({ annualizedReturn }: PortfolioPerformanceProps) {
  return (
    <Card className="dashboard-performance-card">
      <div className="dashboard-card-header performance-header">
        <div className="dashboard-card-title">
          <span className="title-icon"><Icon name="trend" size={22} /></span>
          <h2>Portfolio Performance</h2>
        </div>
        <div className="range-tabs">
          <button>1M</button>
          <button>6M</button>
          <button>1Y</button>
          <button>3Y</button>
          <button className="active">All</button>
        </div>
        <div className="performance-return">
          <strong>{pct(annualizedReturn)}</strong>
          <small>Annualized Return</small>
        </div>
      </div>
      <div className="dashboard-chart-axis">
        <span>$120K</span>
        <span>$100K</span>
        <span>$80K</span>
        <span>$60K</span>
        <span>$40K</span>
      </div>
      <LineChart primary={lineA} height={245} area />
    </Card>
  );
}
