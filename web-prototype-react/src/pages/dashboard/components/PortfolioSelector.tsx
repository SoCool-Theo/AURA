import type { Portfolio } from '../../../types/portfolio';
import { AuraSelect } from '../../../components/ui/AuraSelect';
import type { AuraSelectOption, AuraSelectTone } from '../../../components/ui/AuraSelect';
import { money } from '../../../utils/formatting';

interface PortfolioSelectorProps {
  portfolios: Portfolio[];
  selectedId: string;
  onSelect: (portfolioId: string) => void;
}

export function PortfolioSelector({ portfolios, selectedId, onSelect }: PortfolioSelectorProps) {
  const options: AuraSelectOption<string>[] = portfolios.map(portfolio => {
    const risk = portfolio.riskLevel.toLowerCase();
    const tone: AuraSelectTone = risk.includes('high')
      ? 'red'
      : risk.includes('low')
        ? 'green'
        : 'amber';

    return {
      value: portfolio.id,
      label: portfolio.name,
      description: `${money(portfolio.value)} · ${portfolio.riskLevel}`,
      icon: 'wallet',
      tone,
    };
  });

  return (
    <AuraSelect
      className="dashboard-selector dashboard-aura-select"
      ariaLabel="Select portfolio"
      value={selectedId}
      options={options}
      onChange={onSelect}
    />
  );
}
