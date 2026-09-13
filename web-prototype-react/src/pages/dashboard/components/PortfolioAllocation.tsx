import { isLegacyPortfolioHolding, type PortfolioHoldingResponse } from '../../../types/portfolio';
import { DonutChart } from '../../../components/charts/DonutChart';
import { Card } from '../../../components/ui/Card';
import { formatPercent } from '../dashboardUi';

export function PortfolioAllocation({ holdings }: { holdings: PortfolioHoldingResponse[] }) {
  const allocatedHoldings = holdings.filter(isLegacyPortfolioHolding);
  const chartHoldings = allocatedHoldings.map(item => ({ symbol: item.symbol, weight: item.weight * 100 }));
  return <Card className="dashboard-allocation-card"><div className="dashboard-card-header"><div className="dashboard-card-title"><span className="title-icon allocation-icon">◔</span><h2>Portfolio Allocation</h2></div></div>{allocatedHoldings.length ? <div className="dashboard-allocation-body"><DonutChart holdings={chartHoldings} /><div className="dashboard-legend">{allocatedHoldings.map((item, index) => <div key={item.symbol}><span className={`legend-dot c${index}`} /><span>{item.symbol}</span><strong>{formatPercent(item.weight, 2)}</strong></div>)}</div></div> : <p>No saved allocation is available yet.</p>}</Card>;
}
