import type { Dispatch, SetStateAction } from 'react';
import type { Portfolio } from '../../types/portfolio';
import type { ReportSummary } from '../../types/report';
import { go } from '../../app/routes';
import { PortfolioMetric } from '../../components/portfolio/PortfolioMetric';
import { Icon } from '../../components/ui/Icon';
import { AnalysisSummary } from './components/AnalysisSummary';
import { AssetAnalysisCard } from './components/AssetAnalysisCard';
import { CorrelationHeatmap } from './components/CorrelationHeatmap';
import { RiskDriverTable } from './components/RiskDriverTable';

interface AnalyticsPageProps {
  portfolio: Portfolio;
  setReports: Dispatch<SetStateAction<ReportSummary[]>>;
}

export function AnalyticsPage({ portfolio, setReports }: AnalyticsPageProps) {
  const riskLabel = String(portfolio.riskLevel || 'Moderate').replace(/\s+Risk$/i, '');

  function saveReport() {
    const report: ReportSummary = {
      id: Date.now(),
      portfolioId: portfolio.id,
      name: `${portfolio.name} Analysis`,
      portfolio: portfolio.name,
      type: 'Analysis',
      date: new Date().toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      }),
      riskScore: portfolio.riskScore,
    };
    setReports(previous => [report, ...previous]);
    alert('Analysis snapshot saved to Reports.');
  }

  return (
    <div className="page analytics-page">
      <button className="analytics-back-link" onClick={() => go(`portfolio/${portfolio.id}`)}>
        ← Back to {portfolio.name}
      </button>
      <header className="analytics-header">
        <div><h1>Portfolio Analysis</h1><p>Historical risk report for <strong>{portfolio.name}</strong>.</p></div>
        <div>
          <button className="secondary-btn" onClick={() => go('assistant')}><Icon name="spark" size={17} /> Ask Aura</button>
          <button className="primary-btn" onClick={saveReport}>Save Report <span>↓</span></button>
        </div>
      </header>

      <AnalysisSummary portfolio={portfolio} riskLabel={riskLabel} />

      <div className="analytics-metric-grid">
        <PortfolioMetric label="Annualized Volatility" value="15.32%" detail="Moderate historical variation" icon="trend" tone="purple" />
        <PortfolioMetric label="Maximum Drawdown" value="-21.45%" detail="Historical peak-to-trough" icon="drawdown" tone="red" />
        <PortfolioMetric label="Sharpe Ratio" value="1.24" detail="Good risk-adjusted return" icon="trend" tone="green" />
        <PortfolioMetric label="Diversification" value="56/100" detail="Moderate diversification" icon="shield" tone="amber" />
      </div>

      <div className="analytics-content-grid">
        <RiskDriverTable holdings={portfolio.holdings} />
        <CorrelationHeatmap />
      </div>

      <section className="asset-analysis-section">
        <div className="asset-analysis-heading">
          <div><h2>Individual Asset Analysis</h2><p>Historical risk and performance details for each invested asset.</p></div>
          <button className="secondary-btn" onClick={() => go(`portfolio/${portfolio.id}`)}>View Holdings</button>
        </div>
        <div className="asset-analysis-grid">
          {portfolio.holdings
            .filter(holding => holding.symbol !== 'CASH')
            .map((holding, index) => (
              <AssetAnalysisCard
                key={holding.symbol}
                holding={holding}
                index={index}
                portfolioRiskScore={portfolio.riskScore}
              />
            ))}
        </div>
      </section>
    </div>
  );
}
