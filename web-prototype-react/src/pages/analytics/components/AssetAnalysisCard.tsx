import { Icon } from '../../../components/ui/Icon';
import { SymbolBadge } from '../../../components/ui/SymbolBadge';
import type { AssetMetrics } from '../../../types/analytics';
import { formatNumber, formatPercent } from '../analyticsUi';
import styles from '../AnalyticsIntegration.module.css';

interface AssetAnalysisCardProps {
  asset: AssetMetrics;
  onOpen: () => void;
}

export function AssetAnalysisCard({ asset, onOpen }: AssetAnalysisCardProps) {
  return (
    <button
      type="button"
      className={`card ${styles.asset} ${styles.assetButton}`}
      onClick={onOpen}
      aria-label={`Open ${asset.symbol} risk details`}
    >
      <div className={styles.assetHeader}>
        <SymbolBadge symbol={asset.symbol} />
        <strong>{asset.symbol}</strong>
        <span>{formatPercent(asset.weight, 1)} weight</span>
        <i className={styles.assetChevron}><Icon name="chevron-right" size={18} /></i>
      </div>
      {asset.risk_classification && <p className={styles.assetRiskLevel}>{formatNumber(asset.risk_classification.risk_score, 1)} · {asset.risk_classification.risk_level} risk</p>}
      <dl>
        <div><dt>Cumulative return</dt><dd>{formatPercent(asset.cumulative_return)}</dd></div>
        <div><dt>Annualized return</dt><dd>{formatPercent(asset.annualized_return)}</dd></div>
        <div><dt>Annualized volatility</dt><dd>{formatPercent(asset.annualized_volatility)}</dd></div>
        <div><dt>Maximum drawdown</dt><dd>{formatPercent(asset.max_drawdown)}</dd></div>
        <div><dt>Sharpe ratio</dt><dd>{formatNumber(asset.sharpe_ratio)}</dd></div>
      </dl>
    </button>
  );
}
