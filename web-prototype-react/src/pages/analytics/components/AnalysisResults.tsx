import { useState } from 'react';
import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';
import { go, replace } from '../../../app/routes';
import {
  isPortfolioReportV2,
  isPortfolioReportV3,
  type PortfolioReportResponse,
} from '../../../types/report';
import {
  formatPortfolioAllocation,
  formatPortfolioMoney,
  formatPortfolioQuantity,
} from '../../portfolios/portfolioUi';
import { formatNumber, formatPercent } from '../analyticsUi';
import {
  reportMetricAmountContent,
  reportMonetaryMetrics,
  type ReportMonetaryMetricKey,
} from '../reportMetricDetails';
import {
  RETURN_VIEW_RANGES,
  visibleReturnPoints,
  type ReturnViewRange,
} from '../returnSeriesRange';
import styles from '../AnalyticsIntegration.module.css';
import { AnalysisSummary } from './AnalysisSummary';
import { AssetAnalysisCard } from './AssetAnalysisCard';
import { CorrelationHeatmap } from './CorrelationHeatmap';
import { MetricAmountDialog } from './MetricAmountDialog';
import { RiskDriverTable } from './RiskDriverTable';
import { PortfolioReturnChart } from '../../dashboard/components/PortfolioReturnChart';

type MetricTone = 'primary' | 'success' | 'warning' | 'danger' | 'blue' | 'purple';

function MetricLabel({ icon, label, tone }: { icon: string; label: string; tone: MetricTone }) {
  const toneClass = {
    primary: styles.primaryIcon,
    success: styles.successIcon,
    warning: styles.warningIcon,
    danger: styles.dangerIcon,
    blue: styles.blueIcon,
    purple: styles.purpleIcon,
  }[tone];
  return <small className={styles.metricLabel}><i className={`${styles.metricIcon} ${toneClass}`}><Icon name={icon} size={17} /></i>{label}</small>;
}

export function AnalysisResults({ report }: { report: PortfolioReportResponse }) {
  const analysis = report.analysis;
  const reportV2 = isPortfolioReportV2(report) ? report : null;
  const reportV3 = isPortfolioReportV3(report) ? report : null;
  const monetary = reportMonetaryMetrics(report);
  const [selectedMetric, setSelectedMetric] = useState<ReportMonetaryMetricKey | null>(null);
  const [returnViewRange, setReturnViewRange] = useState<ReturnViewRange>('1Y');
  const metrics = analysis.portfolio_metrics;
  const drawdown = analysis.max_drawdown;
  const diversification = analysis.diversification;
  const concentration = analysis.concentration;
  const visibleReturns = visibleReturnPoints(analysis.portfolio_returns, returnViewRange);

  function openAssetDetail(symbol: string) {
    replace(`reports/${report.portfolio_id}/${report.id}/assets`);
    go(`asset/${report.portfolio_id}/${report.id}/${encodeURIComponent(symbol)}`);
  }

  return (
    <div className={styles.results}>
      <AnalysisSummary analysis={analysis} />

      {reportV3 ? (
        <Card className={styles.snapshotContext}>
          <div className={styles.sectionHeading}>
            <div>
              <small className={styles.contextEyebrow}>SAVED PLANNED ALLOCATION</small>
              <h2>{formatPortfolioMoney(reportV3.baseline.total_proposed_amount, reportV3.baseline.plan_currency)}</h2>
              <p>{reportV3.baseline.hypothetical_notice}</p>
            </div>
            <span className={styles.badge}>{reportV3.baseline.plan_currency}</span>
          </div>
          <div className={styles.contextHoldings}>
            {reportV3.baseline.holdings.map(holding => (
              <div key={holding.id}>
                <strong>{holding.symbol}</strong>
                <span>{formatPortfolioMoney(holding.proposed_amount, reportV3.baseline.plan_currency)}</span>
                <b>{formatPortfolioAllocation(holding.target_allocation)}</b>
              </div>
            ))}
          </div>
          <p className={styles.contextNote}>Target allocation comes from proposed amounts. Estimated shares do not control this analysis.</p>
        </Card>
      ) : reportV2 ? (
        <Card className={styles.snapshotContext}>
          <div className={styles.sectionHeading}>
            <div>
              <small className={styles.contextEyebrow}>SAVED CURRENT VALUATION</small>
              <h2>{formatPortfolioMoney(reportV2.valuation.total_current_value, reportV2.valuation.valuation_currency)}</h2>
              <p>Captured {reportV2.valuation.requested_date} using prices dated {reportV2.valuation.oldest_price_as_of} through {reportV2.valuation.newest_price_as_of}. This snapshot is not revalued.</p>
            </div>
            <span className={styles.badge}>{reportV2.valuation.valuation_currency}</span>
          </div>
          <div className={styles.contextHoldings}>
            {reportV2.holdings.map(holding => (
              <div key={holding.id}>
                <strong>{holding.symbol}</strong>
                <span>{formatPortfolioQuantity(holding.shares)} shares</span>
                <b>{formatPortfolioMoney(holding.current_value, reportV2.valuation.valuation_currency)} · {formatPortfolioAllocation(holding.current_allocation)}</b>
              </div>
            ))}
          </div>
          {reportV2.valuation.fx && <p className={styles.contextNote}>USD/THB {formatPortfolioQuantity(reportV2.valuation.fx.rate)} as of {reportV2.valuation.fx.as_of}</p>}
        </Card>
      ) : (
        <p className={styles.legacyNotice}>Legacy report: results use the allocation weights saved when this analysis was created.</p>
      )}

      <div className={styles.metricGrid}>
        {reportV3 && monetary?.estimated_ending_value != null && <button type="button" className={`card ${styles.metric} ${styles.metricButton}`} onClick={() => setSelectedMetric('endingValue')}><MetricLabel icon="wallet" label="Estimated Value at End of Period" tone={metrics.cumulative_return < 0 ? 'danger' : 'success'} /><i className={styles.metricChevron}><Icon name="chevron-right" size={18} /></i><strong>{formatPortfolioMoney(monetary.estimated_ending_value, monetary.currency)}</strong><span>Historical estimate · Click to understand</span></button>}
        {monetary ? <button type="button" className={`card ${styles.metric} ${styles.metricButton}`} onClick={() => setSelectedMetric('cumulative')}><MetricLabel icon="trend" label="Cumulative Return" tone={metrics.cumulative_return < 0 ? 'danger' : 'success'} /><i className={styles.metricChevron}><Icon name="chevron-right" size={18} /></i><strong>{formatPercent(metrics.cumulative_return)}</strong><span>Saved period · Click for amount</span></button> : <Card className={styles.metric}><MetricLabel icon="trend" label="Cumulative Return" tone={metrics.cumulative_return < 0 ? 'danger' : 'success'} /><strong>{formatPercent(metrics.cumulative_return)}</strong><span>Compounded return for the saved period</span></Card>}
        {monetary ? <button type="button" className={`card ${styles.metric} ${styles.metricButton}`} onClick={() => setSelectedMetric('annualized')}><MetricLabel icon="analytics" label="Annualized Return" tone={metrics.annualized_return < 0 ? 'danger' : 'success'} /><i className={styles.metricChevron}><Icon name="chevron-right" size={18} /></i><strong>{formatPercent(metrics.annualized_return)}</strong><span>Historical equivalent · Click for amount</span></button> : <Card className={styles.metric}><MetricLabel icon="analytics" label="Annualized Return" tone={metrics.annualized_return < 0 ? 'danger' : 'success'} /><strong>{formatPercent(metrics.annualized_return)}</strong><span>Historical annualized portfolio return</span></Card>}
        <Card className={styles.metric}><MetricLabel icon="pulse" label="Annualized Volatility" tone="warning" /><strong>{formatPercent(metrics.annualized_volatility)}</strong><span>Annualized variation over the saved period</span></Card>
        <Card className={styles.metric}><MetricLabel icon="stats-chart" label="Sharpe Ratio" tone="blue" /><strong>{formatNumber(metrics.sharpe_ratio)}</strong><span>Historical risk-adjusted return metric</span></Card>
        {monetary?.maximum_drawdown_amount != null ? <button type="button" className={`card ${styles.metric} ${styles.metricButton}`} onClick={() => setSelectedMetric('drawdown')}><MetricLabel icon="drawdown" label="Maximum Drawdown" tone="danger" /><i className={styles.metricChevron}><Icon name="chevron-right" size={18} /></i><strong>{formatPercent(drawdown.max_drawdown)}</strong><span>{drawdown.peak_date ?? 'N/A'} to {drawdown.trough_date ?? 'N/A'} · Click for amount</span></button> : <Card className={styles.metric}><MetricLabel icon="drawdown" label="Maximum Drawdown" tone="danger" /><strong>{formatPercent(drawdown.max_drawdown)}</strong><span>{drawdown.peak_date ?? 'N/A'} to {drawdown.trough_date ?? 'N/A'}</span></Card>}
        <Card className={styles.metric}><MetricLabel icon="diversification" label="Diversification" tone="primary" /><strong>{formatNumber(diversification.overall_score, 1)}</strong><span>{diversification.level}; {diversification.defined_pair_count}/{diversification.total_pair_count} pairs defined</span></Card>
        <Card className={styles.metric}><MetricLabel icon="pie-chart" label="Largest Weight" tone="purple" /><strong>{formatPercent(concentration.largest_weight)}</strong><span>Top {concentration.top_n} total: {formatPercent(concentration.top_n_weight)}</span></Card>
        <Card className={styles.metric}><MetricLabel icon="assets" label="Effective Assets" tone="blue" /><strong>{formatNumber(concentration.effective_number_of_assets)}</strong><span>HHI {formatNumber(concentration.hhi, 4)}</span></Card>
      </div>

      <RiskDriverTable riskDrivers={analysis.risk_drivers} />

      <section id="per-asset-analysis" className={`card ${styles.section}`} style={{ scrollMarginTop: 18 }}>
        <div className={styles.sectionHeading}>
          <div><h2>{reportV2 ? 'Per-Asset Valuation and Risk' : reportV3 ? 'Planned Asset Risk' : 'Individual Asset Metrics'}</h2><p>Values for the ordered holdings captured by this saved analysis.</p></div>
          <span className={styles.badge}>{analysis.asset_metrics.length} assets</span>
        </div>
        <div className={styles.assetGrid}>
          {analysis.asset_metrics.map(asset => (
            <AssetAnalysisCard
              key={asset.symbol}
              asset={asset}
              onOpen={() => openAssetDetail(asset.symbol)}
            />
          ))}
        </div>
      </section>

      <CorrelationHeatmap matrix={analysis.correlation_matrix} pairs={analysis.correlation_pairs} />

      <Card className={styles.section}>
        <div className={styles.sectionHeading}>
          <div><h2>Portfolio Return Series</h2><p>Ordered historical return observations for this saved period.</p></div>
          <span className={styles.badge}>{analysis.portfolio_returns.length} observations</span>
        </div>
        {analysis.portfolio_returns.length > 0 && <div className={styles.returnChart}>
          <div className={styles.returnChartToolbar}>
            <span>Graph range</span>
            <div className={styles.returnRangeTabs} role="group" aria-label="Portfolio return graph range">
              {RETURN_VIEW_RANGES.map(range => <button type="button" key={range} className={range === returnViewRange ? styles.activeReturnRange : ''} aria-pressed={range === returnViewRange} onClick={() => setReturnViewRange(range)}>{range}</button>)}
            </div>
          </div>
          <PortfolioReturnChart points={visibleReturns} />
          <p className={styles.returnRangeSummary}>Showing {visibleReturns.length} of {analysis.portfolio_returns.length} saved observations · through {analysis.portfolio_returns[analysis.portfolio_returns.length - 1].date}</p>
        </div>}
        <div className={`${styles.tableWrap} ${styles.returnSeriesScroll}`} tabIndex={0} aria-label="Scrollable portfolio return observations">
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

      <p className={styles.education}>Historical analytics and money equivalents are educational. They are not actual profit or loss, forecasts, or investment recommendations.</p>
      <MetricAmountDialog
        content={reportMetricAmountContent(selectedMetric, report)}
        onClose={() => setSelectedMetric(null)}
      />
    </div>
  );
}
