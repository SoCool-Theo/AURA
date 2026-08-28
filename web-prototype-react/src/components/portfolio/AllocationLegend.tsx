import type { Holding } from '../../types/portfolio';

interface AllocationLegendProps {
  holdings: Holding[];
}

export function AllocationLegend({ holdings }: AllocationLegendProps) {
  return (
    <>
      <div className="portfolio-allocation-heading">
        <span>Allocation</span>
        <small>{holdings.length} holdings</small>
      </div>
      <div className="portfolio-card-allocation">
        {holdings.slice(0, 5).map(holding => (
          <span
            key={holding.symbol}
            style={{ width: `${holding.weight}%` }}
            title={`${holding.symbol} ${holding.weight}%`}
          />
        ))}
      </div>
      <div className="holding-chips">
        {holdings.slice(0, 4).map(holding => (
          <span key={holding.symbol}>
            <b>{holding.symbol}</b>
            {holding.weight}%
          </span>
        ))}
        {holdings.length > 4 && (
          <span className="more-holdings">+{holdings.length - 4} more</span>
        )}
      </div>
    </>
  );
}
