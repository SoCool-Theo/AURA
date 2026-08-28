import type { Holding } from '../../../types/portfolio';
import { pct } from '../../../utils/formatting';
import { Card } from '../../../components/ui/Card';
import { RiskPill } from '../../../components/ui/RiskPill';
import { SymbolBadge } from '../../../components/ui/SymbolBadge';

interface AssetAnalysisCardProps {
  holding: Holding;
  index: number;
  portfolioRiskScore: number;
}

export function AssetAnalysisCard({
  holding,
  index,
  portfolioRiskScore,
}: AssetAnalysisCardProps) {
  return (
    <Card className="asset-analysis-card">
      <div className="asset-analysis-card-head">
        <div className="asset-cell">
          <SymbolBadge symbol={holding.symbol} />
          <div><strong>{holding.symbol}</strong><small>{holding.name}</small></div>
        </div>
        <RiskPill score={Math.max(25, portfolioRiskScore - index * 9)} />
      </div>
      <div className="asset-weight-row"><span>Portfolio weight</span><strong>{holding.weight}%</strong></div>
      <div className="asset-weight-bar"><span style={{ width: `${holding.weight}%` }} /></div>
      <dl>
        <div><dt>Annualized return</dt><dd className="green-text">{pct(8 + index * 2.1)}</dd></div>
        <div><dt>Volatility</dt><dd>{(14 + index * 4.2).toFixed(1)}%</dd></div>
        <div><dt>Maximum drawdown</dt><dd className="red-text">-{(18 + index * 7.3).toFixed(1)}%</dd></div>
        <div><dt>Sharpe ratio</dt><dd>{(1.4 - index * .17).toFixed(2)}</dd></div>
      </dl>
    </Card>
  );
}
