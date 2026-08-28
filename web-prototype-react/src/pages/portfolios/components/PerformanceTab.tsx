import type { Portfolio } from '../../../types/portfolio';
import { lineA, lineB } from '../../../mocks/dashboard.mock';
import { pct } from '../../../utils/formatting';
import { LineChart } from '../../../components/charts/LineChart';
import { Card } from '../../../components/ui/Card';

interface PerformanceTabProps {
  portfolio: Portfolio;
}

export function PerformanceTab({ portfolio }: PerformanceTabProps) {
  return (
    <div className="detail-tab-panel performance-tab-layout">
      <Card className="historical-performance-card">
        <div className="detail-card-heading">
          <div><h2>Historical Performance</h2><p>Portfolio performance compared with the S&amp;P 500 benchmark.</p></div>
          <div className="range-tabs"><button>1Y</button><button>3Y</button><button className="active">All</button></div>
        </div>
        <div className="detail-chart-legend"><span className="p-dot" />Your Portfolio <span className="b-dot" />S&amp;P 500</div>
        <LineChart primary={lineA} secondary={lineB} height={330} area />
      </Card>
      <Card className="performance-summary-card">
        <div className="detail-card-heading"><div><h2>Performance Summary</h2><p>Historical risk and return</p></div></div>
        <dl>
          <div><dt>Annualized return</dt><dd className="green-text">{pct(portfolio.totalReturn)}</dd></div>
          <div><dt>Annualized volatility</dt><dd>15.32%</dd></div>
          <div><dt>Maximum drawdown</dt><dd className="red-text">-21.45%</dd></div>
          <div><dt>Sharpe ratio</dt><dd>1.24</dd></div>
          <div><dt>Beta</dt><dd>1.08</dd></div>
        </dl>
        <p>This prototype uses deterministic demo series. Final values will come from Aura's analytics API.</p>
      </Card>
    </div>
  );
}
