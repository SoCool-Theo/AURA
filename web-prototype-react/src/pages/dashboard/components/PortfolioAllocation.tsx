import type { Holding } from '../../../types/portfolio';
import { DonutChart } from '../../../components/charts/DonutChart';
import { Card } from '../../../components/ui/Card';

interface PortfolioAllocationProps {
  holdings: Holding[];
}

interface AllocationItem {
  symbol: string;
  type: string;
  weight: number;
}

export function PortfolioAllocation({ holdings }: PortfolioAllocationProps) {
  const allocation = Object.values(holdings.reduce<Record<string, AllocationItem>>((groups, holding) => {
    const label = holding.type === 'Cash'
      ? 'Cash'
      : holding.type.includes('Bond')
        ? 'Bonds'
        : holding.type.includes('Crypto')
          ? 'Crypto'
          : 'Equity';
    groups[label] = groups[label] || { symbol: label, type: label, weight: 0 };
    groups[label].weight += Number(holding.weight || 0);
    return groups;
  }, {}));

  return (
    <Card className="dashboard-allocation-card">
      <div className="dashboard-card-header">
        <div className="dashboard-card-title">
          <span className="title-icon allocation-icon">◔</span>
          <h2>Portfolio Allocation</h2>
        </div>
      </div>
      <div className="dashboard-allocation-body">
        <DonutChart holdings={allocation} />
        <div className="dashboard-legend">
          {allocation.map((item, index) => (
            <div key={item.symbol}>
              <span className={`legend-dot c${index}`} />
              <span>{item.type}</span>
              <strong>{item.weight.toFixed(1)}%</strong>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}
