import type { Portfolio } from '../../types/portfolio';
import { money, pct } from '../../utils/formatting';
import { Card } from '../ui/Card';
import { SymbolBadge } from '../ui/SymbolBadge';

interface HoldingsTableProps {
  portfolio: Portfolio;
  onViewAll?: () => void;
}

export function HoldingsTable({ portfolio, onViewAll }: HoldingsTableProps) {
  const totalWeight = portfolio.holdings.reduce(
    (sum, holding) => sum + Number(holding.weight || 0),
    0,
  );

  return (
    <Card className="detail-holdings-card">
      <div className="detail-card-heading">
        <div>
          <h2>Holdings</h2>
          <p>{portfolio.holdings.length} assets in this portfolio</p>
        </div>
        {onViewAll && <button onClick={onViewAll}>View all</button>}
      </div>
      <div className="table-scroll">
        <table className="detail-holdings-table">
          <thead>
            <tr>
              <th>Asset</th>
              <th>Weight</th>
              <th>Value</th>
              <th>Daily Change</th>
            </tr>
          </thead>
          <tbody>
            {portfolio.holdings.map(holding => (
              <tr key={holding.symbol}>
                <td>
                  <div className="asset-cell">
                    <SymbolBadge symbol={holding.symbol} />
                    <div>
                      <strong>{holding.symbol}</strong>
                      <small>{holding.name}</small>
                    </div>
                  </div>
                </td>
                <td><strong>{holding.weight}%</strong></td>
                <td>{money(holding.value)}</td>
                <td className={holding.dailyChange > 0 ? 'green-text' : holding.dailyChange < 0 ? 'red-text' : ''}>
                  {holding.dailyChange === 0 ? '—' : pct(holding.dailyChange)}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td>Total</td>
              <td>{totalWeight.toFixed(1)}%</td>
              <td>{money(portfolio.value)}</td>
              <td />
            </tr>
          </tfoot>
        </table>
      </div>
    </Card>
  );
}
