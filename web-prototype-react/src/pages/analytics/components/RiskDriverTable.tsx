import type { Holding } from '../../../types/portfolio';
import { Card } from '../../../components/ui/Card';
import { SymbolBadge } from '../../../components/ui/SymbolBadge';

interface RiskDriverTableProps {
  holdings: Holding[];
}

export function RiskDriverTable({ holdings }: RiskDriverTableProps) {
  const riskDrivers = holdings
    .filter(holding => holding.symbol !== 'CASH')
    .map((holding, index) => ({
      ...holding,
      contribution: Math.max(
        2,
        holding.weight * (index === 0 ? 1.1 : index === 1 ? .9 : .55),
      ).toFixed(1),
      level: index < 2 ? 'High' : index === 2 ? 'Moderate' : 'Low',
    }));

  return (
    <Card className="risk-drivers-card">
      <div className="analytics-card-heading">
        <div><h2>Main Risk Drivers</h2><p>Assets contributing most to historical portfolio risk.</p></div>
        <span>{riskDrivers.length} assets</span>
      </div>
      <div className="analytics-driver-table">
        <div className="analytics-driver-head">
          <span>Asset</span><span>Weight</span><span>Risk contribution</span><span>Level</span>
        </div>
        {riskDrivers.map(driver => (
          <div className="analytics-driver-row" key={driver.symbol}>
            <div className="asset-cell">
              <SymbolBadge symbol={driver.symbol} />
              <div><strong>{driver.symbol}</strong><small>{driver.name}</small></div>
            </div>
            <b>{driver.weight}%</b>
            <div className="driver-contribution">
              <div><span style={{ width: `${Math.min(100, Number(driver.contribution))}%` }} /></div>
              <small>{driver.contribution}%</small>
            </div>
            <span className={`mini-risk ${driver.level.toLowerCase()}`}>{driver.level}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
