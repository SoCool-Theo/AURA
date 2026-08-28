import { useState } from 'react';
import type { Portfolio } from '../../types/portfolio';
import type { UserSettings } from '../../types/settings';
import { AiInsight } from './components/AiInsight';
import { DashboardHeader } from './components/DashboardHeader';
import { DashboardKpiGrid } from './components/DashboardKpiGrid';
import { PortfolioAllocation } from './components/PortfolioAllocation';
import { PortfolioAnalysisCard } from './components/PortfolioAnalysisCard';
import { PortfolioPerformance } from './components/PortfolioPerformance';
import { RiskDrivers } from './components/RiskDrivers';

interface DashboardPageProps {
  portfolios: Portfolio[];
  settings: UserSettings;
}

export function DashboardPage({ portfolios, settings }: DashboardPageProps) {
  const [selectedId, setSelectedId] = useState(portfolios[0]?.id || '');
  const portfolio = portfolios.find(item => item.id === selectedId) || portfolios[0];

  if (!portfolio) return null;

  const firstName = settings?.name?.split(/\s+/)[0] || 'Yan';
  const annualizedReturn = Number(portfolio.annualizedReturn ?? portfolio.totalReturn ?? 0);
  const riskLabel = String(portfolio.riskLevel || 'Moderate').replace(/\s+Risk$/i, '');

  return (
    <div className="page dashboard-page">
      <DashboardHeader
        firstName={firstName}
        portfolios={portfolios}
        selectedId={portfolio.id}
        onSelectPortfolio={setSelectedId}
      />

      <DashboardKpiGrid
        portfolio={portfolio}
        annualizedReturn={annualizedReturn}
        riskLabel={riskLabel}
      />

      <div className="dashboard-primary-grid">
        <PortfolioPerformance annualizedReturn={annualizedReturn} />
        <RiskDrivers portfolioId={portfolio.id} holdings={portfolio.holdings} />
      </div>

      <div className="dashboard-bottom-grid">
        <PortfolioAllocation holdings={portfolio.holdings} />
        <AiInsight riskScore={portfolio.riskScore} riskLabel={riskLabel} />
        <PortfolioAnalysisCard
          portfolioId={portfolio.id}
          riskScore={portfolio.riskScore}
          riskLabel={riskLabel}
        />
      </div>
    </div>
  );
}
