import {
  isLegacyPortfolioHolding,
  type PortfolioResponse,
} from '../../types/portfolio';
import { Card } from '../ui/Card';
import { SymbolBadge } from '../ui/SymbolBadge';

interface HoldingsTableProps {
  portfolio: PortfolioResponse;
  onViewAll?: () => void;
}

export function HoldingsTable({ portfolio, onViewAll }: HoldingsTableProps) {
  const totalWeight = portfolio.holdings.reduce(
    (sum, holding) => sum + (isLegacyPortfolioHolding(holding) ? holding.weight * 100 : 0),
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
              <th>Position</th>
              <th>Symbol</th>
              <th>Allocation</th>
            </tr>
          </thead>
          <tbody>
            {portfolio.holdings.map(holding => (
              <tr key={`${holding.position}-${holding.symbol}`}>
                <td>{holding.position + 1}</td>
                <td>
                  <div className="asset-cell">
                    <SymbolBadge symbol={holding.symbol} />
                    <div><strong>{holding.symbol}</strong></div>
                  </div>
                </td>
                <td><strong>{isLegacyPortfolioHolding(holding) ? `${Number((holding.weight * 100).toFixed(4))}%` : '—'}</strong></td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td />
              <td>Total</td>
              <td>{totalWeight.toFixed(1)}%</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </Card>
  );
}
