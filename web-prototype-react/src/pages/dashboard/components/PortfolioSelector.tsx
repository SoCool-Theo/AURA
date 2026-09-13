import type { PortfolioSummaryResponse } from '../../../types/portfolio';
import { AuraSelect } from '../../../components/ui/AuraSelect';
import type { AuraSelectOption } from '../../../components/ui/AuraSelect';

export function PortfolioSelector({ portfolios, selectedId, onSelect }: { portfolios: PortfolioSummaryResponse[]; selectedId: string; onSelect: (id: string) => void }) {
  const options: AuraSelectOption<string>[] = portfolios.map(portfolio => ({
    value: portfolio.id,
    label: portfolio.name,
    description: portfolio.portfolio_type === 'PLANNED'
      ? `Planned in ${portfolio.plan_currency}`
      : portfolio.portfolio_type === 'LEGACY'
        ? 'Legacy saved allocation'
        : 'Current holdings',
    icon: 'wallet',
    tone: portfolio.portfolio_type === 'PLANNED' ? 'blue' : 'amber',
  }));
  return <AuraSelect className="dashboard-selector dashboard-aura-select" ariaLabel="Select portfolio" value={selectedId} options={options} onChange={onSelect} />;
}
