import type { Portfolio } from '../../../types/portfolio';
import { lineA, lineB } from '../../../mocks/dashboard.mock';
import { money, pct } from '../../../utils/formatting';
import { LineChart } from '../../../components/charts/LineChart';
import { HoldingsTable } from '../../../components/portfolio/HoldingsTable';
import { PortfolioMetric } from '../../../components/portfolio/PortfolioMetric';
import { Card } from '../../../components/ui/Card';

interface PortfolioOverviewTabProps {
  portfolio: Portfolio;
  onViewHoldings: () => void;
}

export function PortfolioOverviewTab({ portfolio, onViewHoldings }: PortfolioOverviewTabProps) {
  const riskLabel = String(portfolio.riskLevel || 'Moderate').replace(/\s+Risk$/i, '');
  const cashPercentage = ((portfolio.cash / portfolio.value) * 100 || 0).toFixed(1);

  return (
    <div className="detail-tab-panel">
      <div className="detail-metric-grid">
        <PortfolioMetric label="Total Value" value={money(portfolio.value)} detail="Current portfolio value" icon="wallet" tone="purple" />
        <PortfolioMetric label="Annualized Return" value={pct(portfolio.totalReturn)} detail="Historical annualized" icon="trend" tone="green" />
        <PortfolioMetric label="Risk Score" value={`${portfolio.riskScore}/100`} detail={riskLabel} icon="shield" tone="amber" />
        <PortfolioMetric label="Cash Position" value={money(portfolio.cash)} detail={`${cashPercentage}% of portfolio`} icon="wallet" tone="blue" />
      </div>
      <div className="detail-overview-grid">
        <HoldingsTable portfolio={portfolio} onViewAll={onViewHoldings} />
        <Card className="detail-performance-card">
          <div className="detail-card-heading">
            <div><h2>Portfolio Performance</h2><p>Cumulative historical return</p></div>
            <div className="range-tabs"><button>1M</button><button>6M</button><button>1Y</button><button>3Y</button><button className="active">All</button></div>
          </div>
          <div className="detail-chart-legend"><span className="p-dot" />Your Portfolio <span className="b-dot" />S&amp;P 500</div>
          <LineChart primary={lineA} secondary={lineB} height={235} area />
          <div className="detail-performance-kpis">
            <div><small>Best Month</small><strong className="green-text">+8.32%</strong><span>Apr 2023</span></div>
            <div><small>Worst Month</small><strong className="red-text">-6.91%</strong><span>Mar 2020</span></div>
            <div><small>Positive Months</small><strong>62%</strong><span>Historical</span></div>
            <div><small>Beta</small><strong>1.08</strong><span>vs S&amp;P 500</span></div>
          </div>
        </Card>
      </div>
    </div>
  );
}
