import type { Portfolio } from '../../../types/portfolio';
import { go } from '../../../app/routes';
import { GaugeChart } from '../../../components/charts/GaugeChart';
import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';

interface AnalysisSummaryProps {
  portfolio: Portfolio;
  riskLabel: string;
}

export function AnalysisSummary({ portfolio, riskLabel }: AnalysisSummaryProps) {
  return (
    <Card className="analysis-summary-hero">
      <div className="analysis-summary-copy">
        <span className="analysis-eyebrow"><Icon name="analysis" size={15} /> OVERALL RISK SUMMARY</span>
        <div className="analysis-score-line">
          <strong>{portfolio.riskScore}<small>/100</small></strong>
          <span>{riskLabel}</span>
        </div>
        <h2>Your portfolio has a {riskLabel.toLowerCase()} historical risk profile.</h2>
        <p>The largest risk comes from concentrated exposure to high-volatility assets and positive correlation between the largest positions. These observations explain historical behavior and are not investment recommendations.</p>
        <div className="analysis-summary-actions">
          <button className="primary-btn" onClick={() => go('assistant')}>Ask Aura About This <span>→</span></button>
          <button className="secondary-btn" onClick={() => go(`simulations/${portfolio.id}`)}>Run What-If Simulation</button>
        </div>
      </div>
      <div className="analysis-gauge-panel">
        <GaugeChart score={portfolio.riskScore} label={riskLabel} />
        <div><span>Last analyzed</span><strong>May 11, 2026</strong></div>
        <small>Based on historical portfolio data</small>
      </div>
    </Card>
  );
}
