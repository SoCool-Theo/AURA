import { usePrivateValue } from '../../../privacy/PortfolioPrivacy';
import { useState, type ReactNode } from 'react';
import type {
  PortfolioPlannedAllocationResponse,
  PortfolioResponse,
  PortfolioValuationResponse,
} from '../../../types/portfolio';
import type { PortfolioReportResponse } from '../../../types/report';
import { Card } from '../../../components/ui/Card';
import { GaugeChart } from '../../../components/charts/GaugeChart';
import { Icon } from '../../../components/ui/Icon';
import { formatPercent } from '../dashboardUi';
import { riskColor } from '../../analytics/analyticsUi';
import { MetricAmountDialog } from '../../analytics/components/MetricAmountDialog';
import {
  reportMetricAmountContent,
  reportMonetaryMetrics,
  type ReportMonetaryMetricKey,
} from '../../analytics/reportMetricDetails';
import {
  formatPortfolioAllocation,
  formatPortfolioMoney,
} from '../../portfolios/portfolioUi';
import styles from '../DashboardIntegration.module.css';

function DashboardKpi({ title, icon, tone, visual, onClick, children }: { title: string; icon: string; tone: string; visual: ReactNode; onClick?: () => void; children: ReactNode }) {
  const content = <><div className="metric-heading"><span className="metric-icon"><Icon name={icon} size={21} /></span><span>{title}</span>{onClick && <span className="dashboard-kpi-chevron"><Icon name="chevron-right" size={20} /></span>}</div><div className="metric-body"><div className="metric-copy">{children}</div><div className="metric-visual">{visual}</div></div></>;
  return onClick
    ? <button type="button" className={`card dashboard-kpi dashboard-kpi-button ${tone}`} onClick={onClick} aria-label={`${title}: show money equivalent`}>{content}</button>
    : <Card className={`dashboard-kpi ${tone}`}>{content}</Card>;
}

export function DashboardKpiGrid({
  portfolio,
  valuation,
  plannedAllocation,
  contextLoading,
  contextFailed,
  report,
  reportLoading,
  reportFailed,
}: {
  portfolio: PortfolioResponse;
  valuation: PortfolioValuationResponse | null;
  plannedAllocation: PortfolioPlannedAllocationResponse | null;
  contextLoading: boolean;
  contextFailed: boolean;
  report: PortfolioReportResponse | null;
  reportLoading: boolean;
  reportFailed: boolean;
}) {
  const privateValue = usePrivateValue();
  const analysis = report?.analysis; const risk = analysis?.risk_classification;
  const monetary = reportMonetaryMetrics(report);
  const [selectedMetric, setSelectedMetric] = useState<ReportMonetaryMetricKey | null>(null);
  const riskKpiTone = !risk ? 'purple' : risk.risk_level === 'Low' ? 'green' : risk.risk_level === 'Moderate' ? 'amber' : 'red';
  const riskLabelTone = !risk ? 'purple-text' : risk.risk_level === 'Low' ? 'positive' : risk.risk_level === 'Moderate' ? 'warning' : 'negative';
  const returnKpiTone = analysis && analysis.portfolio_metrics.annualized_return < 0 ? 'red' : 'green';
  const displayedRiskScore = risk ? Number(risk.risk_score.toFixed(1)) : null;
  const unavailable = reportLoading ? 'Loading…' : 'N/A';
  const status = reportLoading ? 'Loading' : reportFailed ? 'Unavailable' : 'Not analyzed';
  const legacyTotal = portfolio.holdings.reduce(
    (sum, holding) => sum + (holding.weight ?? 0),
    0,
  );
  const valueTitle = portfolio.portfolio_type === 'PLANNED'
    ? 'Proposed Investment'
    : portfolio.portfolio_type === 'LEGACY'
      ? 'Saved Allocation'
      : 'Current Value';
  const value = portfolio.portfolio_type === 'PLANNED'
    ? plannedAllocation
      ? privateValue(formatPortfolioMoney(plannedAllocation.total_proposed_amount, plannedAllocation.plan_currency))
      : contextLoading ? 'Loading…' : 'N/A'
    : portfolio.portfolio_type === 'LEGACY'
      ? formatPortfolioAllocation(legacyTotal)
      : valuation
        ? privateValue(formatPortfolioMoney(valuation.total_current_value, valuation.valuation_currency))
        : contextLoading ? 'Loading…' : 'N/A';
  const valueStatus = contextLoading
    ? 'Loading'
    : contextFailed
      ? 'Unavailable'
      : portfolio.portfolio_type === 'PLANNED'
        ? 'Hypothetical plan'
        : portfolio.portfolio_type === 'LEGACY'
          ? 'Legacy weights'
          : valuation
            ? `Prices through ${valuation.newest_price_as_of}`
            : 'No valuation';
  return <>
    <div className="dashboard-kpis">
      <DashboardKpi title={valueTitle} icon="wallet" tone="blue" visual={<span className={styles.kpiPlaceholder}>{portfolio.portfolio_type === 'PLANNED' ? '◎' : '◈'}</span>}><strong>{value}</strong><span className="metric-change purple-text">{valueStatus}</span></DashboardKpi>
      <DashboardKpi title="Risk Score" icon="speedometer" tone={riskKpiTone} visual={displayedRiskScore !== null ? <GaugeChart score={displayedRiskScore} label="" color={riskColor(risk?.risk_level)} /> : <span className={styles.kpiPlaceholder}>—</span>}><strong style={{ color: riskColor(risk?.risk_level) }}>{risk ? risk.risk_score.toFixed(1) : unavailable}</strong><span className={`metric-change ${riskLabelTone}`} style={{ color: riskColor(risk?.risk_level) }}>{risk?.risk_level ?? status}</span></DashboardKpi>
      <DashboardKpi title="Annualized Return" icon="trend" tone={returnKpiTone} visual={<span className={styles.kpiPlaceholder}>↗</span>} onClick={monetary ? () => setSelectedMetric('annualized') : undefined}><strong>{analysis ? formatPercent(analysis.portfolio_metrics.annualized_return) : unavailable}</strong><span className="metric-change purple-text">{analysis ? monetary ? 'Click for amount' : 'Latest saved report' : status}</span></DashboardKpi>
      <DashboardKpi title="Maximum Drawdown" icon="drawdown" tone="red" visual={<span className={styles.kpiPlaceholder}>↘</span>} onClick={monetary?.maximum_drawdown_amount != null ? () => setSelectedMetric('drawdown') : undefined}><strong>{analysis ? formatPercent(analysis.max_drawdown.max_drawdown) : unavailable}</strong><span className="metric-change negative">{analysis ? monetary?.maximum_drawdown_amount != null ? 'Click for amount' : `${analysis.max_drawdown.peak_date ?? 'N/A'} to ${analysis.max_drawdown.trough_date ?? 'N/A'}` : status}</span></DashboardKpi>
    </div>
    <MetricAmountDialog
      content={reportMetricAmountContent(selectedMetric, report)}
      onClose={() => setSelectedMetric(null)}
    />
  </>;
}
