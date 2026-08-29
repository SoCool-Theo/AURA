import type { PortfolioSummaryResponse } from '../../../types/portfolio';
import { AuraSelect } from '../../../components/ui/AuraSelect';
import type { AuraSelectOption } from '../../../components/ui/AuraSelect';

export function PortfolioSelector({ portfolios, selectedId, onSelect }: { portfolios: PortfolioSummaryResponse[]; selectedId: string; onSelect: (id: string) => void }) {
  const options: AuraSelectOption<string>[] = portfolios.map(portfolio => ({ value: portfolio.id, label: portfolio.name, description: 'Saved portfolio', icon: 'wallet', tone: 'amber' }));
  return <AuraSelect className="dashboard-selector dashboard-aura-select" ariaLabel="Select portfolio" value={selectedId} options={options} onChange={onSelect} />;
}
