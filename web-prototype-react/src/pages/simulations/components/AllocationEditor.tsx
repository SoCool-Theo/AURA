import { useEffect, useState } from 'react';
import type { PortfolioResponse } from '../../../types/portfolio';
import type { SimulationAllocation, SimulationMode } from '../../../types/simulation';
import { Card } from '../../../components/ui/Card';
import { SymbolBadge } from '../../../components/ui/SymbolBadge';
import { isAllocationPercentInput } from '../simulationUi';

interface Props { mode: SimulationMode; portfolio: PortfolioResponse; allocation: SimulationAllocation; totalAllocation: number; disabled?: boolean; onReset: () => void; onChange: (symbol: string, weight: string, selectedSymbols: readonly string[]) => void }

export function AllocationEditor({ mode, portfolio, allocation, totalAllocation, disabled, onReset, onChange }: Props) {
  const symbols = portfolio.holdings.map(holding => holding.symbol);
  const symbolKey = symbols.join('|');
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>(() => symbols.slice(0, 2));
  useEffect(() => setSelectedSymbols(symbols.slice(0, 2)), [portfolio.id, symbolKey]);
  const isValid = Number.isFinite(totalAllocation) && Math.abs(totalAllocation - 100) < .000001;
  const baselineDescription = portfolio.portfolio_type === 'PLANNED'
    ? 'Initialized from this hypothetical plan’s target allocation. Proposed amounts remain unchanged.'
    : portfolio.portfolio_type === 'CURRENT'
      ? 'Initialized from the current USD allocation calculated from saved shares and market values.'
      : 'Initialized from the saved legacy allocation.';
  function toggleTarget(symbol: string) {
    setSelectedSymbols(current => current.includes(symbol)
      ? current.filter(currentSymbol => currentSymbol !== symbol)
      : current.length < 2 ? [...current, symbol] : current);
  }
  return <Card className="simulation-allocation-card">
    <div className="simulation-allocation-header"><div><h2>{mode === 'allocation' ? 'Test a Different Allocation' : 'Modified Allocation for This Scenario'}</h2><p>{baselineDescription} Select exactly two assets. Increasing either target decreases only the other target, while all unselected assets stay unchanged.</p></div><div><button onClick={() => { setSelectedSymbols(symbols.slice(0, 2)); onReset(); }} disabled={disabled}>Reset</button><span className={isValid ? 'valid' : 'invalid'}><small>Total</small><strong>{Number.isFinite(totalAllocation) ? totalAllocation.toFixed(2) : 'Invalid'}%</strong></span></div></div>
    <div className="simulation-allocation-target-status">Selected targets: <strong>{selectedSymbols.length}/2</strong>{selectedSymbols.length === 2 ? ` · ${selectedSymbols.join(' ↔ ')}` : ' · Choose one more asset'}</div>
    <div className="simulation-allocation-grid">{portfolio.holdings.map(holding => {
      const selected = selectedSymbols.includes(holding.symbol);
      const selectionDisabled = Boolean(disabled || (!selected && selectedSymbols.length >= 2));
      return <div
        key={holding.symbol}
        className={`${selected ? 'allocation-target-selected' : ''} ${selectionDisabled ? 'allocation-target-disabled' : ''}`.trim()}
        role="checkbox"
        aria-checked={selected}
        aria-disabled={selectionDisabled}
        tabIndex={selectionDisabled ? -1 : 0}
        onClick={() => { if (!selectionDisabled) toggleTarget(holding.symbol); }}
        onKeyDown={event => {
          if (event.target !== event.currentTarget || selectionDisabled) return;
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            toggleTarget(holding.symbol);
          }
        }}
      >
        <span className="allocation-asset"><SymbolBadge symbol={holding.symbol} /><span><strong>{holding.symbol}</strong><small>Saved position {holding.position + 1}</small></span></span>
        <span className="allocation-target-toggle"><input type="checkbox" checked={selected} readOnly tabIndex={-1} aria-hidden="true" /><span>{selected ? 'Target selected' : 'Select target'}</span></span>
        <span className="allocation-input" onClick={event => event.stopPropagation()}><input aria-label={`${holding.symbol} weight percent`} type="number" min="0" max="100" step="0.01" value={allocation[holding.symbol] ?? ''} onChange={event => { if (isAllocationPercentInput(event.target.value)) onChange(holding.symbol, event.target.value, selectedSymbols); }} onBlur={event => { const percent = Number(event.target.value); if (event.target.value.trim() && Number.isFinite(percent) && percent >= 0 && percent <= 100) onChange(holding.symbol, percent.toFixed(2), selectedSymbols); }} disabled={disabled || !selected || selectedSymbols.length !== 2} /><b>%</b></span>
      </div>;
    })}</div>
    <div className="simulation-allocation-progress"><span><i style={{ width: `${Math.max(0, Math.min(100, Number.isFinite(totalAllocation) ? totalAllocation : 0))}%` }} /></span><p className={isValid ? 'green-text' : 'orange-text'}>{isValid ? 'The displayed total is 100%.' : 'The complete modified allocation must total exactly 100%.'}</p></div>
  </Card>;
}
