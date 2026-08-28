import type { CSSProperties } from 'react';
import type { Portfolio } from '../../../types/portfolio';
import { go } from '../../../app/routes';
import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';
import { SymbolBadge } from '../../../components/ui/SymbolBadge';
import { money } from '../../../utils/formatting';

interface PortfolioContextProps {
  portfolio: Portfolio;
  onAsk: (question: string) => void;
}

export function PortfolioContext({ portfolio, onAsk }: PortfolioContextProps) {
  const riskStyle = {
    '--risk-score': `${portfolio.riskScore * 3.6}deg`,
  } as CSSProperties;

  return (
    <aside className="assistant-context-column">
      <Card className="context-card">
        <div className="context-card-heading">
          <div><span>PORTFOLIO CONTEXT</span><h2>Currently analyzing</h2></div>
          <Icon name="wallet" size={19} />
        </div>
        <div className="context-portfolio">
          <SymbolBadge symbol="TP" />
          <div><strong>{portfolio.name}</strong><small>{money(portfolio.value)} total value</small></div>
        </div>
        <div className="context-risk">
          <div>
            <span>Risk Score</span>
            <strong>{portfolio.riskScore}<small>/100</small></strong>
            <b>Moderate</b>
          </div>
          <div className="context-risk-ring" style={riskStyle}><span>{portfolio.riskScore}</span></div>
        </div>
        <dl>
          <div><dt>Annualized return</dt><dd className="green-text">+12.45%</dd></div>
          <div><dt>Volatility</dt><dd>15.32%</dd></div>
          <div><dt>Max drawdown</dt><dd className="red-text">-21.45%</dd></div>
          <div><dt>Sharpe ratio</dt><dd>1.24</dd></div>
        </dl>
        <button className="secondary-btn context-analysis-btn" onClick={() => go(`analytics/${portfolio.id}`)}>
          View Full Analysis <span>→</span>
        </button>
      </Card>
      <Card className="assistant-drivers-card">
        <div className="context-card-heading"><div><span>TOP RISK DRIVERS</span><h2>What Aura can explain</h2></div></div>
        <div className="assistant-driver">
          <SymbolBadge symbol="NVDA" />
          <span><strong>NVIDIA</strong><small>57.1% concentration</small></span>
          <b className="high">High</b>
        </div>
        <div className="assistant-driver">
          <SymbolBadge symbol="TSLA" />
          <span><strong>Tesla</strong><small>14.4% concentration</small></span>
          <b className="high">High</b>
        </div>
        <button onClick={() => onAsk('Which asset affects my risk the most?')}>
          Ask about risk drivers <span>→</span>
        </button>
      </Card>
      <Card className="assistant-safety-card">
        <Icon name="shield" size={20} />
        <div>
          <strong>Educational guidance</strong>
          <p>Aura explains historical metrics and does not provide investment recommendations.</p>
        </div>
      </Card>
    </aside>
  );
}
