import { useEffect, useMemo, useState } from 'react';
import { addWatchlistItem, deleteWatchlistItem, listWatchlist } from '../../api/watchlistApi';
import { InlineErrorCard, ScreenErrorState } from '../../components/ui/ApiErrorState';
import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import { ConfirmationDialog } from '../../components/ui/ConfirmationDialog';
import type { WatchlistItemResponse } from '../../types/watchlist';
import { supportedAssets } from '../portfolios/supportedAssetSymbols';
import { WatchlistTable } from './components/WatchlistTable';
import { WatchlistToolbar } from './components/WatchlistToolbar';
import { watchlistErrorMessage } from './watchlistUi';

export function WatchlistPage() {
  const [items, setItems] = useState<WatchlistItemResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');
  const [addQuery, setAddQuery] = useState('');
  const [addOpen, setAddOpen] = useState(false);
  const [addingSymbol, setAddingSymbol] = useState<string | null>(null);
  const [removingSymbol, setRemovingSymbol] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [symbolToRemove, setSymbolToRemove] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setLoadError(null);
    void listWatchlist({ signal: controller.signal })
      .then(response => setItems(response.items))
      .catch(error => { if (!controller.signal.aborted) setLoadError(error); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [reloadKey]);

  const filteredItems = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return items;
    return items.filter(item => {
      const name = supportedAssets.find(asset => asset.symbol === item.symbol)?.name ?? '';
      return item.symbol.toLowerCase().includes(normalized) || name.toLowerCase().includes(normalized);
    });
  }, [items, query]);

  const availableAssets = useMemo(() => {
    const existing = new Set(items.map(item => item.symbol));
    const normalized = addQuery.trim().toLowerCase();
    return supportedAssets.filter(asset => !existing.has(asset.symbol) && (
      !normalized
      || asset.symbol.toLowerCase().includes(normalized)
      || asset.name.toLowerCase().includes(normalized)
    ));
  }, [addQuery, items]);

  async function add(symbol: string) {
    if (addingSymbol) return;
    setAddingSymbol(symbol);
    setActionError(null);
    try {
      const added = await addWatchlistItem(symbol);
      setItems(current => [...current, added]);
      setAddQuery('');
      setAddOpen(false);
    } catch (error) {
      setActionError(watchlistErrorMessage(error, 'add'));
    } finally {
      setAddingSymbol(null);
    }
  }

  async function remove(symbol: string) {
    if (removingSymbol) return;
    setRemovingSymbol(symbol);
    setActionError(null);
    try {
      await deleteWatchlistItem(symbol);
      setItems(current => current.filter(item => item.symbol !== symbol));
      setSymbolToRemove(null);
    } catch (error) {
      setActionError(watchlistErrorMessage(error, 'remove'));
    } finally {
      setRemovingSymbol(null);
    }
  }

  return <div className="page watchlist-page">
    <header className="watchlist-header">
      <div><span>MARKET SNAPSHOTS</span><h1>Watchlist</h1><p>Follow supported assets using Aura’s latest saved market data.</p></div>
      <button type="button" className="primary-btn" disabled={loading || Boolean(addingSymbol)} onClick={() => setAddOpen(value => !value)}><span>＋</span>{addOpen ? 'Close Asset Picker' : 'Add Asset'}</button>
    </header>

    {actionError && <div className="watchlist-action-error" role="alert">{actionError}</div>}

    {addOpen && <Card className="watchlist-add-card">
      <div className="watchlist-add-heading"><div><h2>Add a supported asset</h2><p>Assets already in your Watchlist are hidden.</p></div><span>{availableAssets.length} available</span></div>
      <label className="watchlist-add-search"><Icon name="search" size={17} /><input autoFocus aria-label="Search supported assets" placeholder="Search symbol or asset name" value={addQuery} onChange={event => setAddQuery(event.target.value)} /></label>
      <div className="watchlist-add-options">
        {availableAssets.map(asset => <button type="button" key={asset.symbol} disabled={Boolean(addingSymbol)} onClick={() => void add(asset.symbol)}><strong>{asset.symbol}</strong><small>{asset.name}</small><span>{addingSymbol === asset.symbol ? 'Adding…' : 'Add'}</span></button>)}
        {!availableAssets.length && <p>No matching assets are available to add.</p>}
      </div>
    </Card>}

    {loading && !items.length ? <div role="status"><Card className="watchlist-loading"><span className="watchlist-spinner" /><strong>Loading your Watchlist…</strong></Card></div>
      : loadError && !items.length ? <ScreenErrorState error={loadError} resourceName="Watchlist" fallbackMessage="Unable to load your Watchlist." onRetry={() => setReloadKey(value => value + 1)} />
      : <>
        {loadError && <InlineErrorCard error={loadError} stale fallbackMessage="Unable to refresh your Watchlist." onRetry={() => setReloadKey(value => value + 1)} />}
        <Card className="watchlist-library-card">
          <div className="watchlist-library-heading"><div><h2>Tracked assets</h2><p>Latest available prices and backend-calculated changes.</p></div><span className="market-status"><i />Saved market data</span></div>
          {items.length > 0 && <WatchlistToolbar query={query} onQueryChange={setQuery} viewMode={viewMode} onViewChange={setViewMode} />}
          <WatchlistTable assets={filteredItems} totalAssets={items.length} removingSymbol={removingSymbol} viewMode={viewMode} onRemove={symbol => { setActionError(null); setSymbolToRemove(symbol); }} onAdd={() => setAddOpen(true)} onClearSearch={() => setQuery('')} />
        </Card>
      </>}
    <div className="watchlist-education-note"><Icon name="time" size={14} /><p>Prices are the latest saved observations, not live quotes. Updated dates show each asset’s market-data date.</p></div>
    {symbolToRemove && <ConfirmationDialog
      title={`Remove ${symbolToRemove}?`}
      description="This removes the asset from your Watchlist. You can add it again later."
      subjectLabel="Watchlist asset"
      subject={symbolToRemove}
      confirmLabel="Remove Asset"
      busy={removingSymbol === symbolToRemove}
      error={actionError}
      onCancel={() => { if (!removingSymbol) { setSymbolToRemove(null); setActionError(null); } }}
      onConfirm={() => void remove(symbolToRemove)}
    />}
  </div>;
}
