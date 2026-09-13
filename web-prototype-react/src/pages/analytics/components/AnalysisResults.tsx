import { useState } from 'react';
import { Card } from '../../../components/ui/Card';
import {
  isPortfolioReportV2,
  isPortfolioReportV3,
  type PortfolioReportMonetaryMetrics,
  type PortfolioReportResponse,
} from '../../../types/report';
import {
  formatPortfolioAllocation,
  formatPortfolioMoney,
  formatPortfolioQuantity,
  formatSignedPortfolioMoney,
} from '../../portfolios/portfolioUi';
import { formatNumber, formatPercent } from '../analyticsUi';
import styles from '../AnalyticsIntegration.module.css';
import { AnalysisSummary } from './AnalysisSummary';
import { AssetAnalysisCard } from './AssetAnalysisCard';
import { CorrelationHeatmap } from './CorrelationHeatmap';
import {
  MetricAmountDialog,
  type MetricAmountDialogContent,
} from './MetricAmountDialog';
import { RiskDriverTable } from './RiskDriverTable';

type MonetaryMetricKey = 'cumulative' | 'annualized' | 'drawdown';

function metricDialogContent(
  key: MonetaryMetricKey | null,
  monetary: PortfolioReportMonetaryMetrics | null,
  report: PortfolioReportResponse,
): MetricAmountDialogContent | null {
  if (!key || !monetary) return null;
  const metrics = report.analysis.portfolio_metrics;
  const drawdown = report.analysis.max_drawdown;
  const reference = monetary.basis === 'planned-proposed-amount'
    ? `Based on the hypothetical ${formatPortfolioMoney(monetary.reference_amount, monetary.currency)} planned investment saved in this report.`
    : `Based on the ${formatPortfolioMoney(monetary.reference_amount, monetary.currency)} portfolio valuation saved in this report.`;

  if (key === 'cumulative') {
    return {
      title: 'Cumulative Return',
      percentage: formatPercent(metrics.cumulative_return),
      amount: formatSignedPortfolioMoney(monetary.cumulative_return_amount, monetary.currency),
      amountLabel: 'Estimated change over this analysis period',
      reference,
      explanation: `This applies the historical cumulative return from ${report.analysis.start_date} to ${report.analysis.end_date} to the saved reference amount. It is not actual profit or a forecast.`,
      tone: metrics.cumulative_return < 0 ? 'negative' : 'positive',
    };
  }

  if (key === 'annualized') {
    return {
      title: 'Annualized Return',
      percentage: formatPercent(metrics.annualized_return),
      amount: formatSignedPortfolioMoney(monetary.annualized_return_amount, monetary.currency),
      amountLabel: 'Estimated one-year equivalent',
      reference,
      explanation: 'This converts the historical annualized rate into a one-year money equivalent. It is not guaranteed profit, actual account performance, or a forecast.',
      tone: metrics.annualized_return < 0 ? 'negative' : 'positive',
    };
  }

  if (monetary.maximum_drawdown_amount === null) return null;
  const period = drawdown.peak_date && drawdown.trough_date
    ? ` from ${drawdown.peak_date} to ${drawdown.trough_date}`
    : '';
  return {
    title: 'Maximum Drawdown',
    percentage: formatPercent(drawdown.max_drawdown),
    amount: formatSignedPortfolioMoney(monetary.maximum_drawdown_amount, monetary.currency),
    amountLabel: 'Estimated peak-to-trough decline',
    reference,
    explanation: `This is the money equivalent of the same largest historical decline${period}. It is not a prediction of future loss.`,
    tone: 'negative',
  };
}

export function AnalysisResults({ report }: { report: PortfolioReportResponse }) {
  const analysis = report.analysis;
  const reportV2 = isPortfolioReportV2(report) ? report : null;
  const reportV3 = isPortfolioReportV3(report) ? report : null;
  const monetary = reportV3?.monetary_metrics ?? reportV2?.monetary_metrics ?? null;
  const [selectedMetric, setSelectedMetric] = useState<MonetaryMetricKey | null>(null);
  const metrics = analysis.portfolio_metrics;
  const drawdown = analysis.max_drawdown;
  const diversification = analysis.diversification;
  const concentration = analysis.concentration;

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
        {monetary ? <button type="button" className={`card ${styles.metric} ${styles.metricButton}`} onClick={() => setSelectedMetric('cumulative')}><small>Cumulative Return</small><strong>{formatPercent(metrics.cumulative_return)}</strong><span>Saved period · Click for amount</span></button> : <Card className={styles.metric}><small>Cumulative Return</small><strong>{formatPercent(metrics.cumulative_return)}</strong><span>Compounded return for the saved period</span></Card>}
        {monetary ? <button type="button" className={`card ${styles.metric} ${styles.metricButton}`} onClick={() => setSelectedMetric('annualized')}><small>Annualized Return</small><strong>{formatPercent(metrics.annualized_return)}</strong><span>Historical equivalent · Click for amount</span></button> : <Card className={styles.metric}><small>Annualized Return</small><strong>{formatPercent(metrics.annualized_return)}</strong><span>Historical annualized portfolio return</span></Card>}
        <Card className={styles.metric}><small>Annualized Volatility</small><strong>{formatPercent(metrics.annualized_volatility)}</strong><span>Annualized variation over the saved period</span></Card>
        <Card className={styles.metric}><small>Sharpe Ratio</small><strong>{formatNumber(metrics.sharpe_ratio)}</strong><span>Historical risk-adjusted return metric</span></Card>
        {monetary?.maximum_drawdown_amount != null ? <button type="button" className={`card ${styles.metric} ${styles.metricButton}`} onClick={() => setSelectedMetric('drawdown')}><small>Maximum Drawdown</small><strong>{formatPercent(drawdown.max_drawdown)}</strong><span>{drawdown.peak_date ?? 'N/A'} to {drawdown.trough_date ?? 'N/A'} · Click for amount</span></button> : <Card className={styles.metric}><small>Maximum Drawdown</small><strong>{formatPercent(drawdown.max_drawdown)}</strong><span>{drawdown.peak_date ?? 'N/A'} to {drawdown.trough_date ?? 'N/A'}</span></Card>}
        <Card className={styles.metric}><small>Diversification</small><strong>{formatNumber(diversification.overall_score, 1)}</strong><span>{diversification.level}; {diversification.defined_pair_count}/{diversification.total_pair_count} pairs defined</span></Card>
        <Card className={styles.metric}><small>Largest Weight</small><strong>{formatPercent(concentration.largest_weight)}</strong><span>Top {concentration.top_n} total: {formatPercent(concentration.top_n_weight)}</span></Card>
        <Card className={styles.metric}><small>Effective Assets</small><strong>{formatNumber(concentration.effective_number_of_assets)}</strong><span>HHI {formatNumber(concentration.hhi, 4)}</span></Card>
      </div>

      <RiskDriverTable riskDrivers={analysis.risk_drivers} />

      <Card className={styles.section}>
        <div className={styles.sectionHeading}>
          <div><h2>{reportV2 ? 'Per-Asset Valuation and Risk' : reportV3 ? 'Planned Asset Risk' : 'Individual Asset Metrics'}</h2><p>Values for the ordered holdings captured by this saved analysis.</p></div>
          <span className={styles.badge}>{analysis.asset_metrics.length} assets</span>
        </div>
        <div className={styles.assetGrid}>
          {analysis.asset_metrics.map(asset => <AssetAnalysisCard key={asset.symbol} asset={asset} />)}
        </div>
      </Card>

      <CorrelationHeatmap matrix={analysis.correlation_matrix} pairs={analysis.correlation_pairs} />

      <Card className={styles.section}>
        <div className={styles.sectionHeading}>
          <div><h2>Portfolio Return Series</h2><p>Ordered historical return observations for this saved period.</p></div>
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

      <p className={styles.education}>Historical analytics and money equivalents are educational. They are not actual profit or loss, forecasts, or investment recommendations.</p>
      <MetricAmountDialog
        content={metricDialogContent(selectedMetric, monetary, report)}
        onClose={() => setSelectedMetric(null)}
      />
    </div>
  );
}
