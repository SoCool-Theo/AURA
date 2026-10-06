import { Icon } from '../../../components/ui/Icon';
import { go } from '../../../app/routes';
import forecastStyles from '../../forecasting/Forecasting.module.css';
import { SymbolBadge } from '../../../components/ui/SymbolBadge';
import type { WatchlistItemResponse } from '../../../types/watchlist';
import { supportedAssets } from '../../portfolios/supportedAssetSymbols';
import {
  formatWatchlistDate,
  formatWatchlistPercent,
  formatWatchlistPrice,
} from '../watchlistUi';

interface WatchlistTableProps {
  assets: WatchlistItemResponse[];
  totalAssets: number;
  removingSymbol: string | null;
  viewMode: 'list' | 'grid';
  onRemove: (symbol: string) => void;
  onAdd: () => void;
  onClearSearch: () => void;
}

export function WatchlistTable({
  assets,
  totalAssets,
  removingSymbol,
  viewMode,
  onRemove,
  onAdd,
  onClearSearch,
}: WatchlistTableProps) {
  return (
    <>
      {assets.length && viewMode === 'list' ? (
        <div className="watchlist-table-wrap" role="region" aria-label="Tracked assets" tabIndex={0}>
          <table className="watchlist-table">
            <thead>
              <tr>
                <th>Asset</th><th>Latest Price</th><th>Updated</th><th>Daily Change</th><th>YTD Change</th><th aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {assets.map(asset => {
                const name = supportedAssets.find(item => item.symbol === asset.symbol)?.name ?? asset.symbol;
                const dailyTone = asset.daily_change_percent === null
                  ? ''
                  : asset.daily_change_percent >= 0 ? 'positive' : 'negative';
                return (
                <tr key={asset.symbol}>
                  <td>
                    <div className="watchlist-asset-cell">
                      <SymbolBadge symbol={asset.symbol} />
                      <div><strong>{asset.symbol}</strong><small>{name}</small></div>
                    </div>
                  </td>
                  <td><div className="watchlist-price"><strong>{formatWatchlistPrice(asset.latest_price)}</strong><small>{asset.latest_price === null ? 'No saved market data' : 'USD'}</small></div></td>
                  <td><strong className="watchlist-date">{formatWatchlistDate(asset.latest_price_date)}</strong></td>
                  <td>
                    <span className={`watchlist-change ${dailyTone}`}>
                      {formatWatchlistPercent(asset.daily_change_percent)}
                    </span>
                  </td>
                  <td><span className={asset.ytd_change_percent === null ? '' : asset.ytd_change_percent >= 0 ? 'green-text' : 'red-text'}>{formatWatchlistPercent(asset.ytd_change_percent)}</span></td>
                  <td>
                    <button type="button" className={forecastStyles.watchlistLink} onClick={() => go(`forecasting/asset/${encodeURIComponent(asset.symbol)}`)} aria-label={`View ${asset.symbol} outlook`}>View Outlook →</button>
                    <button
                      className="watchlist-remove"
                      onClick={() => onRemove(asset.symbol)}
                      disabled={removingSymbol === asset.symbol}
                      aria-label={`Remove ${asset.symbol} from watchlist`}
                      title="Remove from watchlist"
                    >{removingSymbol === asset.symbol ? '…' : '×'}</button>
                  </td>
                </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : assets.length ? (
        <div className="watchlist-grid" role="region" aria-label="Tracked assets grid">
          {assets.map(asset => {
            const name = supportedAssets.find(item => item.symbol === asset.symbol)?.name ?? asset.symbol;
            const removing = removingSymbol === asset.symbol;
            return <article className="watchlist-grid-card" key={asset.symbol}>
              <header>
                <div className="watchlist-asset-cell"><SymbolBadge symbol={asset.symbol} /><div><strong>{asset.symbol}</strong><small>{name}</small></div></div>
                <button className="watchlist-remove" type="button" onClick={() => onRemove(asset.symbol)} disabled={removing} aria-label={`Remove ${asset.symbol} from watchlist`} title="Remove from watchlist">{removing ? '…' : '×'}</button>
              </header>
              <div className="watchlist-grid-price"><small>Latest Price</small><strong>{formatWatchlistPrice(asset.latest_price)}</strong><span>{asset.latest_price === null ? 'No saved market data' : `Updated ${formatWatchlistDate(asset.latest_price_date)}`}</span></div>
              <div className="watchlist-grid-metrics">
                <div><small>Daily Change</small><strong className={asset.daily_change_percent === null ? '' : asset.daily_change_percent >= 0 ? 'green-text' : 'red-text'}>{formatWatchlistPercent(asset.daily_change_percent)}</strong></div>
                <div><small>YTD Change</small><strong className={asset.ytd_change_percent === null ? '' : asset.ytd_change_percent >= 0 ? 'green-text' : 'red-text'}>{formatWatchlistPercent(asset.ytd_change_percent)}</strong></div>
              </div>
              <button type="button" className={forecastStyles.watchlistLink} onClick={() => go(`forecasting/asset/${encodeURIComponent(asset.symbol)}`)} aria-label={`View ${asset.symbol} outlook`}>View Outlook →</button>
            </article>;
          })}
        </div>
      ) : (
        <div className="watchlist-empty-state">
          <span><Icon name="search" size={27} /></span>
          <h3>{totalAssets ? 'No matching assets' : 'Your watchlist is empty'}</h3>
          <p>{totalAssets ? 'Try a different symbol or company name.' : 'Add an asset to begin tracking market movements.'}</p>
          <button type="button" className="secondary-btn" onClick={totalAssets ? onClearSearch : onAdd}>
            {totalAssets ? 'Clear Search' : 'Add Your First Asset'}
          </button>
        </div>
      )}
      <div className="watchlist-footer">
        <span>Showing <strong>{assets.length}</strong> of <strong>{totalAssets}</strong> tracked assets</span>
        <button type="button" onClick={onAdd}>＋ Add another asset</button>
      </div>
    </>
  );
}
