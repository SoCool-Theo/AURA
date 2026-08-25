import type { ReactNode } from 'react';
import type { Portfolio } from '../../../types/portfolio';
import { downturnA, lineA } from '../../../mocks/dashboard.mock';
import { money, pct } from '../../../utils/formatting';
import { GaugeChart } from '../../../components/charts/GaugeChart';
import { MiniLineChart } from '../../../components/charts/MiniLineChart';
import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';

interface DashboardKpiGridProps {
  portfolio: Portfolio;
  annualizedReturn: number;
  riskLabel: string;
}

interface DashboardKpiProps {
  title: string;
  icon: string;
  tone: string;
  visual: ReactNode;
  children: ReactNode;
}

function DashboardKpi({ title, icon, tone, visual, children }: DashboardKpiProps) {
  return (
    <Card className={`dashboard-kpi ${tone}`}>
      <div className="metric-heading">
        <span className="metric-icon"><Icon name={icon} size={21} /></span>
        <span>{title}</span>
      </div>
      <div className="metric-body">
        <div className="metric-copy">{children}</div>
        <div className="metric-visual">{visual}</div>
      </div>
    </Card>
  );
}

export function DashboardKpiGrid({
  portfolio,
  annualizedReturn,
  riskLabel,
}: DashboardKpiGridProps) {
  return (
    <div className="dashboard-kpis">
      <DashboardKpi
        title="Total Portfolio Value"
        icon="wallet"
        tone="purple"
        visual={<MiniLineChart values={lineA.slice(12)} />}
      >
        <strong>{money(portfolio.value)}</strong>
        <span className="metric-change positive">
          ▲ {money(portfolio.value * .064)} (6.4%)
        </span>
      </DashboardKpi>
      <DashboardKpi
        title="Risk Score"
        icon="shield"
        tone="amber"
        visual={<GaugeChart score={portfolio.riskScore} label="" />}
      >
        <strong>{portfolio.riskScore}</strong>
        <span className="metric-change warning">{riskLabel}</span>
      </DashboardKpi>
      <DashboardKpi
        title="Annualized Return"
        icon="trend"
        tone="purple"
        visual={<MiniLineChart values={lineA.slice(8)} />}
      >
        <strong>{pct(annualizedReturn)}</strong>
        <span className="metric-change purple-text">Annualized</span>
      </DashboardKpi>
      <DashboardKpi
        title="Maximum Drawdown"
        icon="drawdown"
        tone="red"
        visual={<MiniLineChart values={downturnA.slice(6)} />}
      >
        <strong>-21.45%</strong>
        <span className="metric-change negative">Mar 2020</span>
      </DashboardKpi>
    </div>
  );
}
