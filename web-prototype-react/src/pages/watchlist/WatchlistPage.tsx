import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import styles from '../DeferredFeature.module.css';

export function WatchlistPage() {
  return <div className={`page ${styles.page}`}><header className={styles.header}><span>COMING LATER</span><h1>Watchlist</h1><p>A future place to follow assets you want to learn more about.</p></header><Card className={styles.card}><span className={styles.icon}><Icon name="trend" size={28} /></span><span className={styles.badge}>Not available yet</span><h2>Live watchlists are coming later</h2><p>Aura does not currently show live quotes or let you save tracked assets here.</p><div className={styles.facts}><div><strong>No live quotes yet</strong><small>Prices, changes, market caps, and trends will appear only when reliable data is available.</small></div><div><strong>No saved watchlist yet</strong><small>Assets cannot be added or edited on this page right now.</small></div></div></Card></div>;
}
