import { Icon } from '../../../components/ui/Icon';

interface WatchlistToolbarProps {
  query: string;
  onQueryChange: (query: string) => void;
  viewMode: 'list' | 'grid';
  onViewChange: (viewMode: 'list' | 'grid') => void;
}

export function WatchlistToolbar({
  query,
  onQueryChange,
  viewMode,
  onViewChange,
}: WatchlistToolbarProps) {
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
        <div role="group" aria-label="Watchlist view">
          <button type="button" className={viewMode === 'list' ? 'active' : ''} aria-pressed={viewMode === 'list'} onClick={() => onViewChange('list')}><Icon name="reports" size={15} /> List</button>
          <button type="button" className={viewMode === 'grid' ? 'active' : ''} aria-pressed={viewMode === 'grid'} onClick={() => onViewChange('grid')}><Icon name="assets" size={15} /> Grid</button>
        </div>
        <span>Updated dates are shown per asset</span>
      </div>
    </div>
  );
}
