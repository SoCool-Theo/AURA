import type { Portfolio } from '../../../types/portfolio';
import { go } from '../../../app/routes';
import { money } from '../../../utils/formatting';
import { Card } from '../../../components/ui/Card';
import { SymbolBadge } from '../../../components/ui/SymbolBadge';

interface HoldingsTabProps {
  portfolio: Portfolio;
  onUpdateWeight: (symbol: string, nextWeight: string) => void;
}

export function HoldingsTab({ portfolio, onUpdateWeight }: HoldingsTabProps) {
  const totalWeight = portfolio.holdings.reduce(
    (sum, holding) => sum + Number(holding.weight || 0),
    0,
  );

  return (
    <div className="detail-tab-panel">
      <Card className="detail-section-card">
        <div className="detail-section-header">
          <div><h2>Portfolio Holdings</h2><p>Review assets and adjust their prototype allocation weights.</p></div>
          <div className={`allocation-total-badge ${Math.abs(totalWeight - 100) < .2 ? 'valid' : 'invalid'}`}>
            <small>Total allocation</small><strong>{totalWeight.toFixed(1)}%</strong>
          </div>
        </div>
        <div className="detail-edit-holdings">
          <div className="edit-holdings-head"><span>Asset</span><span>Type</span><span>Weight</span><span>Market Value</span></div>
          {portfolio.holdings.map(holding => (
            <div className="edit-holding-row" key={holding.symbol}>
              <div className="asset-cell">
                <SymbolBadge symbol={holding.symbol} />
                <div><strong>{holding.symbol}</strong><small>{holding.name}</small></div>
              </div>
              <span className="asset-type">{holding.type}</span>
              <label>
                <span className="sr-only">{holding.symbol} weight</span>
                <input type="number" min="0" max="100" value={holding.weight} onChange={event => onUpdateWeight(holding.symbol, event.target.value)} />
                <b>%</b>
              </label>
              <strong>{money(holding.value)}</strong>
            </div>
          ))}
        </div>
        <div className="detail-section-footer">
          <p>Changing weights updates this frontend prototype only. Portfolio calculations will use backend data after API integration.</p>
          <button className="primary-btn" onClick={() => go(`analytics/${portfolio.id}`)}>Analyze Allocation</button>
        </div>
      </Card>
    </div>
  );
}
