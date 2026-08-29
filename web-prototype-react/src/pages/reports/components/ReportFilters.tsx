import { Icon } from '../../../components/ui/Icon';
import { AuraSelect } from '../../../components/ui/AuraSelect';
import type { AuraSelectOption } from '../../../components/ui/AuraSelect';
import type { PortfolioSummaryResponse } from '../../../types/portfolio';

interface ReportFiltersProps {
  query: string;
  portfolioId: string;
  portfolios: PortfolioSummaryResponse[];
  onQueryChange: (query: string) => void;
  onPortfolioChange: (portfolioId: string) => void;
  onReset: () => void;
}

export function ReportFilters({
  query,
  portfolioId,
  portfolios,
  onQueryChange,
  onPortfolioChange,
  onReset,
}: ReportFiltersProps) {
  const portfolioOptions: AuraSelectOption<string>[] = [
    { value: '', label: 'All Portfolios', description: 'Saved analyses from every owned portfolio', icon: 'wallet', tone: 'teal' },
    ...portfolios.map(portfolio => ({ value: portfolio.id, label: portfolio.name, description: 'Only this portfolio’s saved reports', icon: 'wallet', tone: 'blue' as const })),
  ];

  return (
    <div className="report-filters">
      <label className="report-search">
        <Icon name="search" size={17} />
        <input
          placeholder="Search by portfolio or report ID..."
          value={query}
          onChange={event => onQueryChange(event.target.value)}
        />
        {query && <button onClick={() => onQueryChange('')} aria-label="Clear search">×</button>}
      </label>
      <AuraSelect className="report-select" ariaLabel="Filter by portfolio" value={portfolioId} options={portfolioOptions} onChange={onPortfolioChange} />
      {(query || portfolioId) && (
        <button className="clear-report-filters" onClick={onReset}>Clear filters</button>
      )}
    </div>
  );
}
