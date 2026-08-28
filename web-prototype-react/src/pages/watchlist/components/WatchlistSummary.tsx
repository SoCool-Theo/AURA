import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';
import type { WatchlistAsset } from '../../../types/market';
import { pct } from '../../../utils/formatting';

interface WatchlistSummaryProps {
  watchlist: WatchlistAsset[];
}

export function WatchlistSummary({ watchlist }: WatchlistSummaryProps) {
  const positiveCount = watchlist.filter(asset => asset.daily > 0).length;
  const averageDaily = watchlist.length
    ? watchlist.reduce((sum, asset) => sum + Number(asset.daily), 0) / watchlist.length
    : 0;
  const topMover = watchlist.length
    ? [...watchlist].sort((first, second) => second.daily - first.daily)[0]
    : null;

  return (
    <div className="watchlist-summary-grid">
      <Card className="watchlist-summary-card">
        <span className="purple"><Icon name="wallet" size={19} /></span>
        <div><small>Tracked Assets</small><strong>{watchlist.length}</strong><p>Saved to your watchlist</p></div>
      </Card>
      <Card className="watchlist-summary-card">
        <span className="green"><Icon name="trend" size={19} /></span>
        <div>
          <small>Positive Today</small>
          <strong>{positiveCount}</strong>
          <p>{watchlist.length ? `${Math.round(positiveCount / watchlist.length * 100)}% of tracked assets` : 'No tracked assets'}</p>
        </div>
      </Card>
      <Card className="watchlist-summary-card">
        <span className={averageDaily >= 0 ? 'blue' : 'red'}>
          <Icon name={averageDaily >= 0 ? 'trend' : 'drawdown'} size={19} />
        </span>
        <div>
          <small>Average Daily Move</small>
          <strong className={averageDaily >= 0 ? 'green-text' : 'red-text'}>{pct(averageDaily)}</strong>
          <p>Across the current list</p>
        </div>
      </Card>
      <Card className="watchlist-summary-card">
        <span className="amber"><Icon name="spark" size={19} /></span>
        <div>
          <small>Top Daily Mover</small>
          <strong>{topMover?.symbol || '—'}</strong>
          <p className={topMover && topMover.daily >= 0 ? 'green-text' : 'red-text'}>
            {topMover ? pct(topMover.daily) : 'No market data'}
          </p>
        </div>
      </Card>
    </div>
  );
}
