import { Icon } from '../../../components/ui/Icon';
import { AuraSelect } from '../../../components/ui/AuraSelect';
import type { AuraSelectOption } from '../../../components/ui/AuraSelect';

export type ReportTypeFilter = 'All Types' | 'Analysis' | 'Simulation' | 'Comparison';

interface ReportFiltersProps {
  query: string;
  portfolio: string;
  portfolios: string[];
  type: ReportTypeFilter;
  onQueryChange: (query: string) => void;
  onPortfolioChange: (portfolio: string) => void;
  onTypeChange: (type: ReportTypeFilter) => void;
  onReset: () => void;
}

export function ReportFilters({
  query,
  portfolio,
  portfolios,
  type,
  onQueryChange,
  onPortfolioChange,
  onTypeChange,
  onReset,
}: ReportFiltersProps) {
  const portfolioOptions: AuraSelectOption<string>[] = [
    { value: 'All Portfolios', label: 'All Portfolios', description: 'Reports from every portfolio', icon: 'wallet', tone: 'teal' },
    ...portfolios.map(name => ({ value: name, label: name, description: `Only reports for ${name}`, icon: 'wallet', tone: 'blue' as const })),
  ];
  const typeOptions: ReadonlyArray<AuraSelectOption<ReportTypeFilter>> = [
    { value: 'All Types', label: 'All report types', description: 'Analysis, simulations, and comparisons', icon: 'reports', tone: 'teal' },
    { value: 'Analysis', label: 'Analysis', description: 'Saved portfolio risk snapshots', icon: 'analysis', tone: 'green' },
    { value: 'Simulation', label: 'Simulation', description: 'Historical what-if scenario reports', icon: 'simulations', tone: 'amber' },
    { value: 'Comparison', label: 'Comparison', description: 'Side-by-side portfolio reports', icon: 'analytics', tone: 'blue' },
  ];

  return (
    <div className="report-filters">
      <label className="report-search">
        <Icon name="search" size={17} />
        <input
          placeholder="Search by report name..."
          value={query}
          onChange={event => onQueryChange(event.target.value)}
        />
        {query && <button onClick={() => onQueryChange('')} aria-label="Clear search">×</button>}
      </label>
      <AuraSelect className="report-select" ariaLabel="Filter by portfolio" value={portfolio} options={portfolioOptions} onChange={onPortfolioChange} />
      <AuraSelect className="report-select" ariaLabel="Filter by report type" value={type} options={typeOptions} onChange={onTypeChange} />
      {(query || portfolio !== 'All Portfolios' || type !== 'All Types') && (
        <button className="clear-report-filters" onClick={onReset}>Clear filters</button>
      )}
    </div>
  );
}
