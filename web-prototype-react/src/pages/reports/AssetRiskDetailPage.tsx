import { useEffect, useState } from 'react';
import { getPortfolioReport } from '../../api/reportsApi';
import { go } from '../../app/routes';
import { PortfolioReturnChart } from '../dashboard/components/PortfolioReturnChart';
import { Card } from '../../components/ui/Card';
import { ScreenErrorState } from '../../components/ui/ApiErrorState';
import { Icon } from '../../components/ui/Icon';
import { SymbolBadge } from '../../components/ui/SymbolBadge';
import { MetricAmountDialog } from '../analytics/components/MetricAmountDialog';
import {
  isPortfolioReportV2,
  isPortfolioReportV3,
  type PortfolioReportResponse,
} from '../../types/report';
import {
  formatPortfolioAllocation,
  formatPortfolioMoney,
  formatPortfolioQuantity,
} from '../portfolios/portfolioUi';
import { formatNumber, formatPercent, formatReportTimestamp } from '../analytics/analyticsUi';
import {
  assetReportMetricAmountContent,
  assetReportMonetaryMetrics,
  type ReportMonetaryMetricKey,
} from '../analytics/reportMetricDetails';
import {
  RETURN_VIEW_RANGES,
  visibleReturnPoints,
  type ReturnViewRange,
} from '../analytics/returnSeriesRange';
import styles from './AssetRiskDetailPage.module.css';

interface AssetRiskDetailPageProps {
  portfolioId: string;
  reportId: string;
  assetSymbol: string;
}

export function AssetRiskDetailPage({
  portfolioId,
  reportId,
  assetSymbol,
}: AssetRiskDetailPageProps) {
  const [report, setReport] = useState<PortfolioReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [range, setRange] = useState<ReturnViewRange>('1Y');
  const [selectedMetric, setSelectedMetric] = useState<ReportMonetaryMetricKey | null>(null);
  const symbol = decodeURIComponent(assetSymbol).toUpperCase();

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setReport(null);
    void getPortfolioReport(portfolioId, reportId, { signal: controller.signal })
      .then(setReport)
      .catch(requestError => {
        if (!controller.signal.aborted) setError(requestError);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [portfolioId, reportId, reloadKey]);

  const backToReport = () => go(`reports/${portfolioId}/${reportId}/assets`);

  if (loading) {
    return <div className={styles.state} role="status"><span className={styles.spinner} /><h2>Loading asset risk</h2><p>Retrieving the saved asset analysis.</p></div>;
  }

  if (error || !report) {
    return <ScreenErrorState error={error ?? 'Report not found.'} fallbackMessage="Unable to retrieve this asset analysis." resourceName="Asset analysis" onRetry={() => setReloadKey(key => key + 1)} onBack={backToReport} backTitle="Back to Report" />;
  }

  const asset = report.analysis.asset_metrics.find(metric => metric.symbol === symbol);
  if (!asset) {
    return <ScreenErrorState error={`${symbol} is not part of this saved report.`} fallbackMessage="Asset analysis not found." resourceName="Asset analysis" onBack={backToReport} backTitle="Back to Report" />;
  }

  const risk = asset.risk_classification;
  const driver = report.analysis.risk_drivers.entries.find(entry => entry.symbol === symbol);
  const series = report.analysis.asset_returns?.find(item => item.symbol === symbol);
  const visiblePoints = visibleReturnPoints(series?.points ?? [], range);
  const reportV2 = isPortfolioReportV2(report) ? report : null;
  const reportV3 = isPortfolioReportV3(report) ? report : null;
  const currentHolding = reportV2?.holdings.find(holding => holding.symbol === symbol);
  const plannedHolding = reportV3?.baseline.holdings.find(holding => holding.symbol === symbol);
  const assetMonetary = assetReportMonetaryMetrics(report, symbol);
  const scoreTone = !risk
    ? styles.unavailable
    : risk.risk_level === 'Low'
      ? styles.low
      : risk.risk_level === 'Moderate'
        ? styles.moderate
        : styles.high;

  return (
    <div className={`page ${styles.page}`}>
      <button className={styles.backLink} onClick={backToReport}>← Report <span>/</span> {symbol}</button>
      <header className={styles.header}>
        <div className={styles.identity}>
          <SymbolBadge symbol={symbol} />
          <div>
            <small>ASSET RISK DETAIL</small>
            <h1>{symbol}</h1>
            <p>{report.analysis.portfolio_name} · Saved {formatReportTimestamp(report.created_at)}</p>
          </div>
        </div>
        <span className={styles.snapshotBadge}>Immutable Snapshot</span>
      </header>

      <section className={styles.heroGrid}>
        <Card className={styles.summaryCard}>
          <small>HISTORICAL ASSET RISK</small>
          <h2>{risk ? `${risk.risk_level} risk` : 'Risk score unavailable'}</h2>
          <p>Calculated for the same saved observation period as the portfolio report.</p>
          {risk ? <ul>{risk.reasons.map(reason => <li key={reason}>{reason}</li>)}</ul> : <p className={styles.legacyMessage}>This older report predates per-asset risk classification.</p>}
        </Card>
        <Card className={`${styles.scoreCard} ${scoreTone}`}>
          <Icon name="speedometer" size={24} />
          <strong>{risk ? formatNumber(risk.risk_score, 1) : 'N/A'}</strong>
          <span>{risk ? `${risk.risk_level} risk` : 'Legacy report'}</span>
        </Card>
      </section>

      <section className={styles.metricGrid}>
        <Metric label="Portfolio weight" value={formatPercent(asset.weight)} />
        <Metric label="Cumulative return" value={formatPercent(asset.cumulative_return)} onOpen={assetMonetary ? () => setSelectedMetric('cumulative') : undefined} />
        <Metric label="Annualized return" value={formatPercent(asset.annualized_return)} onOpen={assetMonetary ? () => setSelectedMetric('annualized') : undefined} />
        <Metric label="Annualized volatility" value={formatPercent(asset.annualized_volatility)} />
        <Metric label="Maximum drawdown" value={formatPercent(asset.max_drawdown)} onOpen={assetMonetary?.maximum_drawdown_amount != null ? () => setSelectedMetric('drawdown') : undefined} />
        <Metric label="Sharpe ratio" value={formatNumber(asset.sharpe_ratio)} />
      </section>

      <Card className={styles.chartCard}>
        <div className={styles.sectionHeading}>
          <div><h2>Historical Return Series</h2><p>Periodic {symbol} returns frozen with this report.</p></div>
          <span>{series?.points.length ?? 0} observations</span>
        </div>
        {series?.points.length ? <>
          <div className={styles.rangeTabs} role="group" aria-label={`${symbol} return graph range`}>
            {RETURN_VIEW_RANGES.map(option => <button type="button" key={option} className={option === range ? styles.activeRange : ''} aria-pressed={option === range} onClick={() => setRange(option)}>{option}</button>)}
          </div>
          <PortfolioReturnChart points={visiblePoints} axisLabel={`${symbol} return (%)`} ariaLabel={`Saved periodic ${symbol} returns by date`} />
          <p className={styles.observationSummary}>Showing {visiblePoints.length} of {series.points.length} saved observations.</p>
        </> : <div className={styles.emptySeries}><Icon name="time" size={24} /><strong>Historical asset graph unavailable</strong><p>This report was created before per-asset series were stored. Run a new analysis to create the graph.</p></div>}
      </Card>

      <section className={styles.detailGrid}>
        <Card className={styles.detailCard}>
          <div className={styles.sectionHeading}><div><h2>Portfolio Impact</h2><p>How {symbol} contributed to this portfolio’s saved volatility.</p></div></div>
          {driver ? <dl>
            <Detail label="Risk-driver rank" value={`#${driver.rank}`} />
            <Detail label="Risk contribution" value={formatPercent(driver.percentage_volatility_contribution)} />
            <Detail label="Component contribution" value={formatPercent(driver.component_volatility_contribution)} />
            <Detail label="Marginal contribution" value={formatPercent(driver.marginal_volatility_contribution)} />
          </dl> : <p className={styles.legacyMessage}>Portfolio-impact details are unavailable.</p>}
        </Card>

        <Card className={styles.detailCard}>
          <div className={styles.sectionHeading}><div><h2>Saved Position</h2><p>Snapshot context associated with this asset.</p></div></div>
          <dl>
            {currentHolding && reportV2 ? <>
              <Detail label="Current value" value={formatPortfolioMoney(currentHolding.current_value, reportV2.valuation.valuation_currency)} />
              <Detail label="Shares" value={formatPortfolioQuantity(currentHolding.shares)} />
              <Detail label="Saved allocation" value={formatPortfolioAllocation(currentHolding.current_allocation)} />
              <Detail label="Price date" value={currentHolding.price_as_of} />
            </> : plannedHolding && reportV3 ? <>
              <Detail label="Proposed amount" value={formatPortfolioMoney(plannedHolding.proposed_amount, reportV3.baseline.plan_currency)} />
              <Detail label="Target allocation" value={formatPortfolioAllocation(plannedHolding.target_allocation)} />
              <Detail label="Portfolio mode" value="Hypothetical plan" />
            </> : <Detail label="Saved allocation" value={formatPercent(asset.weight)} />}
          </dl>
        </Card>
      </section>

      <p className={styles.education}>Historical asset analytics are educational. They are not forecasts or investment recommendations.</p>
      <MetricAmountDialog
        content={assetReportMetricAmountContent(selectedMetric, report, symbol)}
        onClose={() => setSelectedMetric(null)}
      />
    </div>
  );
}

function Metric({ label, value, onOpen }: { label: string; value: string; onOpen?: () => void }) {
  const content = <><small>{label}</small>{onOpen && <i className={styles.metricChevron}><Icon name="chevron-right" size={17} /></i>}<strong>{value}</strong>{onOpen && <span>Click for amount</span>}</>;
  return onOpen
    ? <button type="button" className={`card ${styles.metric} ${styles.metricButton}`} onClick={onOpen} aria-label={`${label}: ${value}. Show money equivalent.`}>{content}</button>
    : <Card className={styles.metric}>{content}</Card>;
}

function Detail({ label, value }: { label: string; value: string }) {
  return <div><dt>{label}</dt><dd>{value}</dd></div>;
}
