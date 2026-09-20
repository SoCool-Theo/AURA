import type { PortfolioResponse } from '../../../types/portfolio';
import type { SimulationAllocation, SimulationMode } from '../../../types/simulation';
import { Card } from '../../../components/ui/Card';
import { SymbolBadge } from '../../../components/ui/SymbolBadge';

interface Props { mode: SimulationMode; portfolio: PortfolioResponse; allocation: SimulationAllocation; totalAllocation: number; disabled?: boolean; onReset: () => void; onChange: (symbol: string, weight: string) => void }

export function AllocationEditor({ mode, portfolio, allocation, totalAllocation, disabled, onReset, onChange }: Props) {
  const isValid = Number.isFinite(totalAllocation) && Math.abs(totalAllocation - 100) < .000001;
  const baselineDescription = portfolio.portfolio_type === 'PLANNED'
    ? 'Initialized from this hypothetical plan’s target allocation. Proposed amounts remain unchanged.'
    : portfolio.portfolio_type === 'CURRENT'
      ? 'Initialized from the current USD allocation calculated from saved shares and market values.'
      : 'Initialized from the saved legacy allocation.';
  return <Card className="simulation-allocation-card">
    <div className="simulation-allocation-header"><div><h2>{mode === 'allocation' ? 'Test a Different Allocation' : 'Modified Allocation for This Scenario'}</h2><p>{baselineDescription} Change these percentages only to test a hypothetical alternative.</p></div><div><button onClick={onReset} disabled={disabled}>Reset</button><span className={isValid ? 'valid' : 'invalid'}><small>Total</small><strong>{Number.isFinite(totalAllocation) ? totalAllocation.toFixed(2) : 'Invalid'}%</strong></span></div></div>
    <div className="simulation-allocation-grid">{portfolio.holdings.map(holding => <label key={holding.symbol}><span className="allocation-asset"><SymbolBadge symbol={holding.symbol} /><span><strong>{holding.symbol}</strong><small>Saved position {holding.position + 1}</small></span></span><span className="allocation-input"><input aria-label={`${holding.symbol} weight percent`} type="number" step="any" value={allocation[holding.symbol] ?? ''} onChange={event => onChange(holding.symbol, event.target.value)} disabled={disabled} /><b>%</b></span></label>)}</div>
    <div className="simulation-allocation-progress"><span><i style={{ width: `${Math.max(0, Math.min(100, Number.isFinite(totalAllocation) ? totalAllocation : 0))}%` }} /></span><p className={isValid ? 'green-text' : 'orange-text'}>{isValid ? 'The displayed total is 100%.' : 'The complete modified allocation must total exactly 100%.'}</p></div>
  </Card>;
}
