import { Card } from '../../../components/ui/Card';
import type { PortfolioAnalysisResponse } from '../../../types/analytics';
import { formatNumber, formatPercent } from '../analyticsUi';
import styles from '../AnalyticsIntegration.module.css';
import { AnalysisSummary } from './AnalysisSummary';
import { AssetAnalysisCard } from './AssetAnalysisCard';
import { CorrelationHeatmap } from './CorrelationHeatmap';
import { RiskDriverTable } from './RiskDriverTable';

export function AnalysisResults({ analysis }: { analysis: PortfolioAnalysisResponse }) {
  const metrics = analysis.portfolio_metrics;
  const drawdown = analysis.max_drawdown;
  const diversification = analysis.diversification;
  const concentration = analysis.concentration;

  return (
    <div className={styles.results}>
      <AnalysisSummary analysis={analysis} />

      <div className={styles.metricGrid}>
        <Card className={styles.metric}><small>Cumulative Return</small><strong>{formatPercent(metrics.cumulative_return)}</strong><span>Compounded return for the saved period</span></Card>
        <Card className={styles.metric}><small>Annualized Return</small><strong>{formatPercent(metrics.annualized_return)}</strong><span>Backend annualized portfolio return</span></Card>
        <Card className={styles.metric}><small>Annualized Volatility</small><strong>{formatPercent(metrics.annualized_volatility)}</strong><span>Backend annualized variation</span></Card>
        <Card className={styles.metric}><small>Sharpe Ratio</small><strong>{formatNumber(metrics.sharpe_ratio)}</strong><span>Backend risk-adjusted return metric</span></Card>
        <Card className={styles.metric}><small>Maximum Drawdown</small><strong>{formatPercent(drawdown.max_drawdown)}</strong><span>{drawdown.peak_date ?? 'N/A'} to {drawdown.trough_date ?? 'N/A'}</span></Card>
        <Card className={styles.metric}><small>Diversification</small><strong>{formatNumber(diversification.overall_score, 1)}</strong><span>{diversification.level}; {diversification.defined_pair_count}/{diversification.total_pair_count} pairs defined</span></Card>
        <Card className={styles.metric}><small>Largest Weight</small><strong>{formatPercent(concentration.largest_weight)}</strong><span>Top {concentration.top_n} total: {formatPercent(concentration.top_n_weight)}</span></Card>
        <Card className={styles.metric}><small>Effective Assets</small><strong>{formatNumber(concentration.effective_number_of_assets)}</strong><span>HHI {formatNumber(concentration.hhi, 4)}</span></Card>
      </div>

      <RiskDriverTable riskDrivers={analysis.risk_drivers} />

      <Card className={styles.section}>
        <div className={styles.sectionHeading}>
          <div><h2>Individual Asset Metrics</h2><p>Values returned for the ordered holdings captured by this analysis.</p></div>
          <span className={styles.badge}>{analysis.asset_metrics.length} assets</span>
        </div>
        <div className={styles.assetGrid}>
          {analysis.asset_metrics.map(asset => <AssetAnalysisCard key={asset.symbol} asset={asset} />)}
        </div>
      </Card>

      <CorrelationHeatmap matrix={analysis.correlation_matrix} pairs={analysis.correlation_pairs} />

      <Card className={styles.section}>
        <div className={styles.sectionHeading}>
          <div><h2>Portfolio Return Series</h2><p>Ordered backend return observations; no cumulative value series is calculated in React.</p></div>
          <span className={styles.badge}>{analysis.portfolio_returns.length} observations</span>
        </div>
        <div className={styles.tableWrap}>
          <table className={styles.dataTable}>
            <thead><tr><th>Date</th><th>Portfolio return</th></tr></thead>
            <tbody>{analysis.portfolio_returns.map(point => (
              <tr key={point.date}><td>{point.date}</td><td className={point.portfolio_return < 0 ? styles.signedNegative : ''}>{formatPercent(point.portfolio_return, 4)}</td></tr>
            ))}</tbody>
          </table>
        </div>
      </Card>

      <Card className={styles.section}>
        <div className={styles.sectionHeading}><div><h2>Analysis Metadata</h2><p>Requested dates and the actual observation coverage are shown separately.</p></div></div>
        <div className={styles.metadata}>
          <div><small>Requested start</small><strong>{analysis.start_date}</strong></div>
          <div><small>Requested end</small><strong>{analysis.end_date}</strong></div>
          <div><small>Analysis start</small><strong>{analysis.metadata.analysis_start}</strong></div>
          <div><small>Analysis end</small><strong>{analysis.metadata.analysis_end}</strong></div>
          <div><small>Price observations</small><strong>{analysis.metadata.price_observation_count}</strong></div>
          <div><small>Return observations</small><strong>{analysis.metadata.return_observation_count}</strong></div>
          <div><small>Asset count</small><strong>{analysis.metadata.asset_count}</strong></div>
          <div><small>Average correlation</small><strong>{formatNumber(diversification.average_pairwise_correlation)}</strong></div>
          <div><small>Weight score</small><strong>{formatNumber(diversification.weight_score, 1)}</strong></div>
          <div><small>Correlation score</small><strong>{formatNumber(diversification.correlation_score, 1)}</strong></div>
        </div>
      </Card>

      <p className={styles.education}>Historical analytics are educational and are not investment recommendations. All financial metrics shown above come from the saved backend analysis response.</p>
    </div>
  );
}
