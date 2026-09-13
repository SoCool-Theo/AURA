import {
  isLegacyPortfolioHolding,
  type PortfolioHoldingResponse,
} from '../../types/portfolio';

interface AllocationLegendProps {
  holdings: PortfolioHoldingResponse[];
}

export function AllocationLegend({ holdings }: AllocationLegendProps) {
  const allocatedHoldings = holdings.filter(isLegacyPortfolioHolding);

  return (
    <>
      <div className="portfolio-allocation-heading">
        <span>Allocation</span>
        <small>{holdings.length} holdings</small>
      </div>
      <div className="portfolio-card-allocation">
        {allocatedHoldings.slice(0, 5).map(holding => (
          <span
            key={holding.symbol}
            style={{ width: `${holding.weight * 100}%` }}
            title={`${holding.symbol} ${(holding.weight * 100).toFixed(2)}%`}
          />
        ))}
      </div>
      <div className="holding-chips">
        {allocatedHoldings.slice(0, 4).map(holding => (
          <span key={holding.symbol}>
            <b>{holding.symbol}</b>
            {Number((holding.weight * 100).toFixed(4))}%
          </span>
        ))}
        {allocatedHoldings.length > 4 && (
          <span className="more-holdings">+{allocatedHoldings.length - 4} more</span>
        )}
      </div>
    </>
  );
}
