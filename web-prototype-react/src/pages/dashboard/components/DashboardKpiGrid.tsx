import type { ReactNode } from 'react';
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
import {
  formatPortfolioAllocation,
  formatPortfolioMoney,
} from '../../portfolios/portfolioUi';
import styles from '../DashboardIntegration.module.css';

function DashboardKpi({ title, icon, tone, visual, children }: { title: string; icon: string; tone: string; visual: ReactNode; children: ReactNode }) { return <Card className={`dashboard-kpi ${tone}`}><div className="metric-heading"><span className="metric-icon"><Icon name={icon} size={21} /></span><span>{title}</span></div><div className="metric-body"><div className="metric-copy">{children}</div><div className="metric-visual">{visual}</div></div></Card>; }

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
  const analysis = report?.analysis; const risk = analysis?.risk_classification;
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
      ? formatPortfolioMoney(plannedAllocation.total_proposed_amount, plannedAllocation.plan_currency)
      : contextLoading ? 'Loading…' : 'N/A'
    : portfolio.portfolio_type === 'LEGACY'
      ? formatPortfolioAllocation(legacyTotal)
      : valuation
        ? formatPortfolioMoney(valuation.total_current_value, valuation.valuation_currency)
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
  return <div className="dashboard-kpis">
    <DashboardKpi title={valueTitle} icon="wallet" tone="purple" visual={<span className={styles.kpiPlaceholder}>{portfolio.portfolio_type === 'PLANNED' ? '◎' : '◈'}</span>}><strong>{value}</strong><span className="metric-change purple-text">{valueStatus}</span></DashboardKpi>
    <DashboardKpi title="Risk Score" icon="shield" tone="amber" visual={displayedRiskScore !== null ? <GaugeChart score={displayedRiskScore} label="" /> : <span className={styles.kpiPlaceholder}>—</span>}><strong>{risk ? risk.risk_score.toFixed(1) : unavailable}</strong><span className="metric-change warning">{risk?.risk_level ?? status}</span></DashboardKpi>
    <DashboardKpi title="Annualized Return" icon="trend" tone="purple" visual={<span className={styles.kpiPlaceholder}>↗</span>}><strong>{analysis ? formatPercent(analysis.portfolio_metrics.annualized_return) : unavailable}</strong><span className="metric-change purple-text">{analysis ? 'Latest saved report' : status}</span></DashboardKpi>
    <DashboardKpi title="Maximum Drawdown" icon="drawdown" tone="red" visual={<span className={styles.kpiPlaceholder}>↘</span>}><strong>{analysis ? formatPercent(analysis.max_drawdown.max_drawdown) : unavailable}</strong><span className="metric-change negative">{analysis ? `${analysis.max_drawdown.peak_date ?? 'N/A'} to ${analysis.max_drawdown.trough_date ?? 'N/A'}` : status}</span></DashboardKpi>
  </div>;
}
