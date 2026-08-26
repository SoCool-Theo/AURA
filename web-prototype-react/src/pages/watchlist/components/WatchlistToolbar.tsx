import { Icon } from '../../../components/ui/Icon';

interface WatchlistToolbarProps {
  query: string;
  onQueryChange: (query: string) => void;
}

export function WatchlistToolbar({ query, onQueryChange }: WatchlistToolbarProps) {
  return (
    <div className="watchlist-toolbar">
      <label>
        <Icon name="search" size={17} />
        <input
          placeholder="Search by symbol or company name..."
          value={query}
          onChange={event => onQueryChange(event.target.value)}
        />
        {query && <button onClick={() => onQueryChange('')} aria-label="Clear search">×</button>}
      </label>
      <div className="watchlist-view-controls">
        <button className="active"><Icon name="reports" size={15} /> List</button>
        <span>Last updated May 11, 2026</span>
      </div>
    </div>
  );
}
