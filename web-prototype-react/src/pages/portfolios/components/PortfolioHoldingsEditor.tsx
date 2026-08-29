import { useEffect, useRef, useState } from 'react';
import { replacePortfolioHoldings } from '../../../api/portfoliosApi';
import { Card } from '../../../components/ui/Card';
import type { PortfolioResponse } from '../../../types/portfolio';
import styles from '../PortfolioIntegration.module.css';
import {
  displayPercentage,
  portfolioErrorMessage,
  requestWeight,
} from '../portfolioUi';

type EditableHolding = {
  id: number;
  symbol: string;
  percentage: string;
};

function editableHoldings(portfolio: PortfolioResponse): EditableHolding[] {
  if (!portfolio.holdings.length) {
    return [{ id: 0, symbol: '', percentage: '100' }];
  }
  return portfolio.holdings.map((holding, index) => ({
    id: index,
    symbol: holding.symbol,
    percentage: displayPercentage(holding.weight),
  }));
}

function validationError(holdings: EditableHolding[]): string | null {
  if (!holdings.length) return 'Add at least one holding.';
  if (holdings.some(holding => !holding.symbol.trim())) {
    return 'Enter a symbol for every holding.';
  }

  const percentages = holdings.map(holding => Number(holding.percentage));
  if (percentages.some(weight => !Number.isFinite(weight) || weight < 0 || weight > 100)) {
    return 'Each allocation must be a number from 0% to 100%.';
  }
  const total = percentages.reduce((sum, weight) => sum + weight, 0);
  if (Math.abs(total - 100) > 1e-7) {
    return `Displayed allocations total ${Number(total.toFixed(10))}%; they must total 100%.`;
  }
  return null;
}

type PortfolioHoldingsEditorProps = {
  portfolio: PortfolioResponse;
  onSaved: (portfolio: PortfolioResponse) => void;
};

export function PortfolioHoldingsEditor({
  portfolio,
  onSaved,
}: PortfolioHoldingsEditorProps) {
  const nextId = useRef(portfolio.holdings.length || 1);
  const [holdings, setHoldings] = useState(() => editableHoldings(portfolio));
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const totalPercentage = holdings.reduce((sum, holding) => (
    sum + (Number(holding.percentage) || 0)
  ), 0);

  useEffect(() => {
    setHoldings(editableHoldings(portfolio));
    nextId.current = portfolio.holdings.length || 1;
  }, [portfolio]);

  function updateHolding(id: number, update: Partial<EditableHolding>) {
    setHoldings(previous => previous.map(holding => (
      holding.id === id ? { ...holding, ...update } : holding
    )));
    setError(null);
  }

  function moveHolding(index: number, direction: -1 | 1) {
    const destination = index + direction;
    if (destination < 0 || destination >= holdings.length) return;
    const next = [...holdings];
    [next[index], next[destination]] = [next[destination], next[index]];
    setHoldings(next);
  }

  async function save() {
    const invalid = validationError(holdings);
    if (invalid) {
      setError(invalid);
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const updated = await replacePortfolioHoldings(portfolio.id, {
        holdings: holdings.map(holding => ({
          symbol: holding.symbol.trim(),
          weight: requestWeight(holding.percentage),
        })),
      });
      onSaved(updated);
    } catch (requestError) {
      setError(portfolioErrorMessage(requestError, 'Unable to replace portfolio holdings.'));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="detail-tab-panel">
      <Card className="detail-section-card">
        <div className="detail-section-header">
          <div><h2>Complete Holdings Replacement</h2><p>Saving replaces the entire ordered allocation. Symbols are entered manually.</p></div>
          <div className={`allocation-total-badge ${Math.abs(totalPercentage - 100) <= 1e-7 ? 'valid' : 'invalid'}`}>
            <small>Total allocation</small><strong>{Number(totalPercentage.toFixed(10))}%</strong>
          </div>
        </div>

        {error && <p className={styles.error} role="alert">{error}</p>}

        <div className="table-scroll">
          <table className={styles.holdingTable}>
            <thead><tr><th>Order</th><th>Symbol</th><th>Allocation (%)</th><th>Actions</th></tr></thead>
            <tbody>{holdings.map((holding, index) => (
              <tr key={holding.id}>
                <td>{index + 1}</td>
                <td><input aria-label={`Holding ${index + 1} symbol`} value={holding.symbol} onChange={event => updateHolding(holding.id, { symbol: event.target.value })} /></td>
                <td><input aria-label={`${holding.symbol || `Holding ${index + 1}`} allocation percentage`} type="number" min="0" max="100" step="0.01" value={holding.percentage} onChange={event => updateHolding(holding.id, { percentage: event.target.value })} /></td>
                <td><div className={styles.orderActions}>
                  <button aria-label={`Move holding ${index + 1} up`} onClick={() => moveHolding(index, -1)} disabled={index === 0}>↑</button>
                  <button aria-label={`Move holding ${index + 1} down`} onClick={() => moveHolding(index, 1)} disabled={index === holdings.length - 1}>↓</button>
                  <button className={styles.dangerButton} aria-label={`Remove holding ${index + 1}`} onClick={() => { setHoldings(previous => previous.filter(item => item.id !== holding.id)); setError(null); }}>×</button>
                </div></td>
              </tr>
            ))}</tbody>
          </table>
        </div>

        <div className="detail-section-footer">
          <p>Displayed percentages are divided by 100 once at the request boundary. Backend normalization and validation remain authoritative.</p>
          <div className={styles.editorActions}>
            <button className="secondary-btn" onClick={() => {
              const id = nextId.current;
              nextId.current += 1;
              setHoldings(previous => [...previous, { id, symbol: '', percentage: '0' }]);
              setError(null);
            }}>＋ Add holding</button>
            <button className="primary-btn" onClick={() => void save()} disabled={saving}>{saving ? 'Saving…' : 'Save complete allocation'}</button>
          </div>
        </div>
      </Card>
    </div>
  );
}
