import { marketDataPresentation } from './marketDataPresentation';
import { useMarketDataRefresh } from './useMarketDataRefresh';
import styles from './MarketDataStatus.module.css';

type Props = { market: ReturnType<typeof useMarketDataRefresh>; symbols: string[]; busy?: boolean };
export function MarketDataStatus({ market, symbols, busy = false }: Props) {
  const info = marketDataPresentation(market.status, market.unavailable, symbols);
  return <div className={styles.row}>
    <div className={styles.copy} role="status" aria-live="polite">
      <span className={styles[info.tone]}><i aria-hidden="true" />{info.title}</span>
      <small>{info.detail}</small>
    </div>
    <button type="button" className={styles.refresh} disabled={market.refreshing || busy} onClick={market.refresh} aria-label="Refresh saved market data">{market.refreshing || busy ? 'Refreshing…' : 'Refresh'}</button>
  </div>;
}
