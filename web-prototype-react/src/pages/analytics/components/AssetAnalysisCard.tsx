import { Card } from '../../../components/ui/Card';
import { SymbolBadge } from '../../../components/ui/SymbolBadge';
import type { AssetMetrics } from '../../../types/analytics';
import { formatNumber, formatPercent } from '../analyticsUi';
import styles from '../AnalyticsIntegration.module.css';

interface AssetAnalysisCardProps {
  asset: AssetMetrics;
}

export function AssetAnalysisCard({ asset }: AssetAnalysisCardProps) {
  return (
    <Card className={styles.asset}>
      <div className={styles.assetHeader}>
        <SymbolBadge symbol={asset.symbol} />
        <strong>{asset.symbol}</strong>
        <span>{formatPercent(asset.weight, 1)} weight</span>
      </div>
      <dl>
        <div><dt>Cumulative return</dt><dd>{formatPercent(asset.cumulative_return)}</dd></div>
        <div><dt>Annualized return</dt><dd>{formatPercent(asset.annualized_return)}</dd></div>
        <div><dt>Annualized volatility</dt><dd>{formatPercent(asset.annualized_volatility)}</dd></div>
        <div><dt>Maximum drawdown</dt><dd>{formatPercent(asset.max_drawdown)}</dd></div>
        <div><dt>Sharpe ratio</dt><dd>{formatNumber(asset.sharpe_ratio)}</dd></div>
      </dl>
    </Card>
  );
}
