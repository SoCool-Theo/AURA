import type { PortfolioSummaryResponse } from '../../../types/portfolio';

export function PortfolioSelector({ portfolios, selectedId, onSelect }: { portfolios: PortfolioSummaryResponse[]; selectedId: string; onSelect: (id: string) => void }) {
  return <div className="dashboard-portfolio-picker">
    <span className="dashboard-portfolio-picker-label">SELECTED PORTFOLIO</span>
    <div className="dashboard-portfolio-options" role="radiogroup" aria-label="Select portfolio">
      {portfolios.map(portfolio => {
        const selected = portfolio.id === selectedId;
        return <button
          type="button"
          role="radio"
          aria-checked={selected}
          className={`dashboard-portfolio-option ${selected ? 'active' : ''}`}
          key={portfolio.id}
          onClick={() => onSelect(portfolio.id)}
        >
          {portfolio.name}
        </button>;
      })}
    </div>
  </div>;
}
