import type { Holding } from '../../../types/portfolio';
import { go } from '../../../app/routes';
import { Card } from '../../../components/ui/Card';
import { SymbolBadge } from '../../../components/ui/SymbolBadge';

interface RiskDriversProps {
  portfolioId: string;
  holdings: Holding[];
}

export function RiskDrivers({ portfolioId, holdings }: RiskDriversProps) {
  const riskDrivers = holdings.filter(holding => holding.symbol !== 'CASH').slice(0, 3);

  return (
    <Card className="dashboard-risk-card">
      <div className="dashboard-card-header">
        <div className="dashboard-card-title"><h2>Top Risk Drivers</h2></div>
        <button className="text-btn" onClick={() => go(`analytics/${portfolioId}`)}>View all</button>
      </div>
      <div className="dashboard-risk-list">
        {riskDrivers.map((holding, index) => (
          <div key={holding.symbol}>
            <SymbolBadge symbol={holding.symbol} />
            <div>
              <strong>{holding.name}</strong>
              <small>{holding.symbol}</small>
            </div>
            <b>{holding.weight}%</b>
            <span className={`mini-risk ${index < 2 ? 'high' : 'moderate'}`}>
              {index < 2 ? 'High' : 'Medium'}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}
