import { Icon } from '../../../components/ui/Icon';

export type ReportTypeFilter = 'All Types' | 'Analysis' | 'Simulation' | 'Comparison';

interface ReportFiltersProps {
  query: string;
  type: ReportTypeFilter;
  onQueryChange: (query: string) => void;
  onTypeChange: (type: ReportTypeFilter) => void;
  onReset: () => void;
}

export function ReportFilters({
  query,
  type,
  onQueryChange,
  onTypeChange,
  onReset,
}: ReportFiltersProps) {
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
      <label className="report-select">
        <Icon name="wallet" size={16} />
        <select aria-label="Filter by portfolio"><option>All Portfolios</option></select>
        <Icon name="chevron-down" size={14} />
      </label>
      <label className="report-select">
        <Icon name="reports" size={16} />
        <select
          value={type}
          onChange={event => onTypeChange(event.target.value as ReportTypeFilter)}
          aria-label="Filter by report type"
        >
          <option>All Types</option>
          <option>Analysis</option>
          <option>Simulation</option>
          <option>Comparison</option>
        </select>
        <Icon name="chevron-down" size={14} />
      </label>
      {(query || type !== 'All Types') && (
        <button className="clear-report-filters" onClick={onReset}>Clear filters</button>
      )}
    </div>
  );
}
