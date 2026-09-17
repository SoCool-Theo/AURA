import {
  isLegacyPortfolioHolding,
  isPlannedPortfolioHolding,
  isRealPortfolioHolding,
  type PortfolioPlannedPreviewResponse,
  type PortfolioResponse,
  type PortfolioValuationResponse,
} from '../../types/portfolio';
import {
  formatPortfolioAllocation,
  formatPortfolioMoney,
  formatPortfolioQuantity,
} from '../../pages/portfolios/portfolioUi';
import { Card } from '../ui/Card';
import { SymbolBadge } from '../ui/SymbolBadge';

function estimatedSharesLabel(
  preview: PortfolioPlannedPreviewResponse['holdings'][number] | undefined,
): string {
  if (preview?.estimate_status === 'AVAILABLE' && preview.estimated_shares != null) {
    return formatPortfolioQuantity(preview.estimated_shares);
  }
  if (preview?.estimate_status === 'FX_UNAVAILABLE') return 'FX unavailable';
  if (preview?.estimate_status === 'PRICE_UNAVAILABLE') return 'Price unavailable';
  return 'Unavailable';
}

interface HoldingsTableProps {
  portfolio: PortfolioResponse;
  valuation?: PortfolioValuationResponse | null;
  plannedPreview?: PortfolioPlannedPreviewResponse | null;
  onViewAll?: () => void;
}

export function HoldingsTable({
  portfolio,
  valuation = null,
  plannedPreview = null,
  onViewAll,
}: HoldingsTableProps) {
  const current = portfolio.portfolio_type === 'CURRENT';
  const planned = portfolio.portfolio_type === 'PLANNED';
  const totalWeight = portfolio.holdings.reduce(
    (sum, holding) => sum + (isLegacyPortfolioHolding(holding) ? holding.weight * 100 : 0),
    0,
  );
  const valuationBySymbol = new Map(
    valuation?.holdings.map(holding => [holding.symbol, holding]) ?? [],
  );
  const previewBySymbol = new Map(
    plannedPreview?.holdings.map(holding => [holding.symbol, holding]) ?? [],
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
              {current ? <>
                <th>Quantity Owned</th>
                <th>Current Value</th>
                <th>Current Allocation</th>
              </> : planned ? <>
                <th>Proposed Amount</th>
                <th>Estimated Shares</th>
                <th>Target Allocation</th>
              </> : <th>Saved Allocation</th>}
            </tr>
          </thead>
          <tbody>
            {portfolio.holdings.map(holding => {
              const valued = valuationBySymbol.get(holding.symbol);
              const preview = previewBySymbol.get(holding.symbol);
              return <tr key={`${holding.position}-${holding.symbol}`}>
                <td>{holding.position + 1}</td>
                <td>
                  <div className="asset-cell">
                    <SymbolBadge symbol={holding.symbol} />
                    <div><strong>{holding.symbol}</strong></div>
                  </div>
                </td>
                {current && isRealPortfolioHolding(holding) ? <>
                  <td>{formatPortfolioQuantity(holding.shares)}</td>
                  <td><strong>{valued ? formatPortfolioMoney(valued.current_value, valuation?.valuation_currency ?? 'USD') : '—'}</strong></td>
                  <td><strong>{valued ? formatPortfolioAllocation(valued.current_allocation) : '—'}</strong></td>
                </> : planned && isPlannedPortfolioHolding(holding) ? <>
                  <td>{formatPortfolioMoney(holding.proposed_amount, portfolio.plan_currency ?? 'USD')}</td>
                  <td>{estimatedSharesLabel(preview)}</td>
                  <td><strong>{preview ? formatPortfolioAllocation(preview.target_allocation) : '—'}</strong></td>
                </> : (
                  <td><strong>{isLegacyPortfolioHolding(holding) ? formatPortfolioAllocation(holding.weight) : '—'}</strong></td>
                )}
              </tr>;
            })}
          </tbody>
          <tfoot>
            <tr>
              <td />
              <td>Total</td>
              {current ? <>
                <td />
                <td>{valuation ? formatPortfolioMoney(valuation.total_current_value, valuation.valuation_currency) : '—'}</td>
                <td>{valuation ? '100.00%' : '—'}</td>
              </> : planned ? <>
                <td>{plannedPreview ? formatPortfolioMoney(plannedPreview.total_proposed_amount, plannedPreview.plan_currency) : '—'}</td>
                <td />
                <td>{plannedPreview ? '100.00%' : '—'}</td>
              </> : <td>{totalWeight.toFixed(1)}%</td>}
            </tr>
          </tfoot>
        </table>
      </div>
    </Card>
  );
}
