import type { Portfolio } from '../../../types/portfolio';
import type { SimulationAllocation, SimulationMode } from '../../../types/simulation';
import { Card } from '../../../components/ui/Card';
import { SymbolBadge } from '../../../components/ui/SymbolBadge';

interface AllocationEditorProps {
  mode: SimulationMode;
  portfolio: Portfolio;
  allocation: SimulationAllocation;
  totalAllocation: number;
  onReset: () => void;
  onChange: (symbol: string, weight: number) => void;
}

export function AllocationEditor({
  mode,
  portfolio,
  allocation,
  totalAllocation,
  onReset,
  onChange,
}: AllocationEditorProps) {
  const isValid = Math.abs(totalAllocation - 100) < .01;

  return (
    <Card className="simulation-allocation-card">
      <div className="simulation-allocation-header">
        <div>
          <h2>{mode === 'Allocation Change' ? 'Test a Different Allocation' : 'Modified Allocation for This Scenario'}</h2>
          <p>Adjust weights while keeping the total allocation at 100%.</p>
        </div>
        <div>
          <button onClick={onReset}>Reset</button>
          <span className={isValid ? 'valid' : 'invalid'}>
            <small>Total</small><strong>{totalAllocation.toFixed(1)}%</strong>
          </span>
        </div>
      </div>
      <div className="simulation-allocation-grid">
        {portfolio.holdings.map(holding => (
          <label key={holding.symbol}>
            <span className="allocation-asset">
              <SymbolBadge symbol={holding.symbol} />
              <span><strong>{holding.symbol}</strong><small>{holding.type}</small></span>
            </span>
            <span className="allocation-input">
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                value={allocation[holding.symbol]}
                onChange={event => onChange(holding.symbol, Number(event.target.value))}
              />
              <b>%</b>
            </span>
          </label>
        ))}
      </div>
      <div className="simulation-allocation-progress">
        <span><i style={{ width: `${Math.min(100, totalAllocation)}%` }} /></span>
        <p className={isValid ? 'green-text' : 'orange-text'}>
          {isValid ? 'Allocation is ready to simulate.' : 'Allocation must total 100% before running.'}
        </p>
      </div>
    </Card>
  );
}
