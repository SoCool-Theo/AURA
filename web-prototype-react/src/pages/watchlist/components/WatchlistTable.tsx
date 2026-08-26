import { MiniLineChart } from '../../../components/charts/MiniLineChart';
import { Icon } from '../../../components/ui/Icon';
import { SymbolBadge } from '../../../components/ui/SymbolBadge';
import { downturnA, lineA } from '../../../mocks/dashboard.mock';
import type { WatchlistAsset } from '../../../types/market';
import { money, pct } from '../../../utils/formatting';

interface WatchlistTableProps {
  assets: WatchlistAsset[];
  totalAssets: number;
  onRemove: (symbol: string) => void;
  onAdd: () => void;
  onClearSearch: () => void;
}

export function WatchlistTable({
  assets,
  totalAssets,
  onRemove,
  onAdd,
  onClearSearch,
}: WatchlistTableProps) {
  return (
    <>
      {assets.length ? (
        <div className="watchlist-table-wrap" role="region" aria-label="Tracked assets" tabIndex={0}>
          <table className="watchlist-table">
            <thead>
              <tr>
                <th>Asset</th><th>Price</th><th>Daily Change</th><th>YTD Change</th><th>Market Cap</th><th>Trend</th><th aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {assets.map((asset, index) => (
                <tr key={asset.symbol}>
                  <td>
                    <div className="watchlist-asset-cell">
                      <SymbolBadge symbol={asset.symbol} />
                      <div><strong>{asset.symbol}</strong><small>{asset.name}</small></div>
                    </div>
                  </td>
                  <td><div className="watchlist-price"><strong>{money(asset.price)}</strong><small>USD</small></div></td>
                  <td>
                    <span className={`watchlist-change ${asset.daily >= 0 ? 'positive' : 'negative'}`}>
                      {asset.daily >= 0 ? '↑' : '↓'} {pct(asset.daily)}
                    </span>
                  </td>
                  <td><span className={asset.yearly >= 0 ? 'green-text' : 'red-text'}>{pct(asset.yearly)}</span></td>
                  <td><strong className="watchlist-cap">{asset.cap}</strong></td>
                  <td>
                    <div className={`watchlist-spark ${asset.daily >= 0 ? 'positive' : 'negative'}`}>
                      <MiniLineChart values={(asset.daily >= 0 ? lineA : downturnA).slice(index, index + 10)} />
                    </div>
                  </td>
                  <td>
                    <button
                      className="watchlist-remove"
                      onClick={() => onRemove(asset.symbol)}
                      aria-label={`Remove ${asset.symbol} from watchlist`}
                      title="Remove from watchlist"
                    >×</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="watchlist-empty-state">
          <span><Icon name="search" size={27} /></span>
          <h3>{totalAssets ? 'No matching assets' : 'Your watchlist is empty'}</h3>
          <p>{totalAssets ? 'Try a different symbol or company name.' : 'Add an asset to begin tracking market movements.'}</p>
          <button className="secondary-btn" onClick={totalAssets ? onClearSearch : onAdd}>
            {totalAssets ? 'Clear Search' : 'Add Your First Asset'}
          </button>
        </div>
      )}
      <div className="watchlist-footer">
        <span>Showing <strong>{assets.length}</strong> of <strong>{totalAssets}</strong> tracked assets</span>
        <button onClick={onAdd}>＋ Add another asset</button>
      </div>
    </>
  );
}
