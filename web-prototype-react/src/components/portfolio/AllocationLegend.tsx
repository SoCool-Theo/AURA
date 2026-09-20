import type { PortfolioAllocationDisplayHolding } from '../../pages/portfolios/portfolioUi';

const allocationColors = [
  'var(--purple-primary)',
  'var(--blue-primary)',
  'var(--teal-primary)',
  'var(--amber-primary)',
  '#a855f7',
];

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
        {holdings.map((holding, index) => (
          <span
            key={holding.symbol}
            style={{
              width: `${holding.weight * 100}%`,
              backgroundColor: allocationColors[index % allocationColors.length],
            }}
            title={`${holding.symbol} ${(holding.weight * 100).toFixed(2)}%`}
          />
        ))}
      </div>
      <div className="holding-chips">
        {holdings.map((holding, index) => (
          <span key={holding.symbol}>
            <i
              aria-hidden="true"
              style={{ backgroundColor: allocationColors[index % allocationColors.length] }}
            />
            <b>{holding.symbol}</b>
            <em>{(holding.weight * 100).toFixed(2)}%</em>
          </span>
        ))}
      </div>
    </>
  );
}
