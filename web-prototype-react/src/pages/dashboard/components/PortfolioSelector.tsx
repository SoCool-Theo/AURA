import type { Portfolio } from '../../../types/portfolio';
import { Icon } from '../../../components/ui/Icon';

interface PortfolioSelectorProps {
  portfolios: Portfolio[];
  selectedId: string;
  onSelect: (portfolioId: string) => void;
}

export function PortfolioSelector({ portfolios, selectedId, onSelect }: PortfolioSelectorProps) {
  return (
    <label className="dashboard-selector">
      <Icon name="wallet" size={19} />
      <span className="sr-only">Portfolio</span>
      <select value={selectedId} onChange={event => onSelect(event.target.value)}>
        {portfolios.map(portfolio => (
          <option key={portfolio.id} value={portfolio.id}>{portfolio.name}</option>
        ))}
      </select>
      <span className="selector-chevron"><Icon name="chevron-down" size={17} /></span>
    </label>
  );
}
