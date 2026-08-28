import { useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import type { WatchlistAsset } from '../../types/market';
import { WatchlistSummary } from './components/WatchlistSummary';
import { WatchlistTable } from './components/WatchlistTable';
import { WatchlistToolbar } from './components/WatchlistToolbar';

interface WatchlistPageProps {
  watchlist: WatchlistAsset[];
  setWatchlist: Dispatch<SetStateAction<WatchlistAsset[]>>;
}

export function WatchlistPage({ watchlist, setWatchlist }: WatchlistPageProps) {
  const [query, setQuery] = useState('');
  const normalizedQuery = query.toLowerCase();
  const visibleAssets = watchlist.filter(asset => (
    asset.symbol.toLowerCase().includes(normalizedQuery)
    || asset.name.toLowerCase().includes(normalizedQuery)
  ));

  function addAsset() {
    const symbol = prompt('Symbol (e.g. AMZN)');
    if (!symbol) return;

    const cleanSymbol = symbol.trim().toUpperCase();
    if (watchlist.some(asset => asset.symbol === cleanSymbol)) {
      alert('Already in watchlist.');
      return;
    }

    setWatchlist(previous => [
      ...previous,
      {
        symbol: cleanSymbol,
        name: `${cleanSymbol} demo asset`,
        price: 100,
        daily: 0,
        yearly: 0,
        cap: '—',
      },
    ]);
  }

  function removeAsset(symbol: string) {
    setWatchlist(previous => previous.filter(asset => asset.symbol !== symbol));
  }

  return (
    <div className="page watchlist-page">
      <header className="watchlist-header">
        <div>
          <span>MARKET MONITOR</span>
          <h1>Watchlist</h1>
          <p>Track assets you are interested in and review their recent market movement.</p>
        </div>
        <button className="primary-btn" onClick={addAsset}><span>＋</span> Add Asset</button>
      </header>

      <WatchlistSummary watchlist={watchlist} />

      <Card className="watchlist-library-card">
        <div className="watchlist-library-heading">
          <div>
            <h2>Tracked Assets</h2>
            <p>Market values shown here are prototype data for portfolio-risk education.</p>
          </div>
          <div className="market-status"><i /><span>Market data available</span></div>
        </div>

        <WatchlistToolbar query={query} onQueryChange={setQuery} />
        <WatchlistTable
          assets={visibleAssets}
          totalAssets={watchlist.length}
          onRemove={removeAsset}
          onAdd={addAsset}
          onClearSearch={() => setQuery('')}
        />
      </Card>

      <div className="watchlist-education-note">
        <Icon name="shield" size={16} />
        <p>Watchlist performance is historical market information for education and does not represent a recommendation to buy or sell.</p>
      </div>
    </div>
  );
}
