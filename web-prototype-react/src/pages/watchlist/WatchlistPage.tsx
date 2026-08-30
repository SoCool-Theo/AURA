import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import styles from '../DeferredFeature.module.css';

export function WatchlistPage() {
  return <div className={`page ${styles.page}`}><header className={styles.header}><span>DEFERRED MARKET FEATURE</span><h1>Watchlist</h1><p>A future place to monitor assets after customer market-data APIs are available.</p></header><Card className={styles.card}><span className={styles.icon}><Icon name="trend" size={28} /></span><span className={styles.badge}>Not connected</span><h2>Live watchlists are not available yet</h2><p>Aura currently has no customer Watchlist, quote, market-cap, or trend endpoint. Fabricated prices and browser-persisted asset records are not shown or editable here.</p><div className={styles.facts}><div><strong>No live quotes</strong><small>Prices, changes, market caps, and spark lines require a supported API.</small></div><div><strong>No browser watchlist</strong><small>Tracked assets are not stored as production records in local storage.</small></div></div></Card></div>;
}
