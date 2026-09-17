import type { PortfolioAllocationDisplayHolding } from '../../pages/portfolios/portfolioUi';

interface AllocationLegendProps {
  holdings: PortfolioAllocationDisplayHolding[];
  label?: string;
}

export function AllocationLegend({ holdings, label = 'Allocation' }: AllocationLegendProps) {
  return (
    <>
      <div className="portfolio-allocation-heading">
        <span>{label}</span>
        <small>{holdings.length} holdings</small>
      </div>
      <div className="portfolio-card-allocation">
        {holdings.slice(0, 5).map(holding => (
          <span
            key={holding.symbol}
            style={{ width: `${holding.weight * 100}%` }}
            title={`${holding.symbol} ${(holding.weight * 100).toFixed(2)}%`}
          />
        ))}
      </div>
      <div className="holding-chips">
        {holdings.slice(0, 4).map(holding => (
          <span key={holding.symbol}>
            <b>{holding.symbol}</b>
            {Number((holding.weight * 100).toFixed(4))}%
          </span>
        ))}
        {holdings.length > 4 && (
          <span className="more-holdings">+{holdings.length - 4} more</span>
        )}
      </div>
    </>
  );
}
