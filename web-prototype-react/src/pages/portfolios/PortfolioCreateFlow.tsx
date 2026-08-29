import { useRef, useState } from 'react';
import {
  createPortfolio,
  replacePortfolioHoldings,
} from '../../api/portfoliosApi';
import { go } from '../../app/routes';
import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import type { PortfolioResponse } from '../../types/portfolio';
import styles from './PortfolioIntegration.module.css';
import { portfolioErrorMessage, requestWeight } from './portfolioUi';

type DraftHolding = {
  id: number;
  symbol: string;
  percentage: string;
};

function validateHoldings(holdings: DraftHolding[]): string | null {
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

export function PortfolioCreateFlow() {
  const nextHoldingId = useRef(1);
  const [name, setName] = useState('');
  const [holdings, setHoldings] = useState<DraftHolding[]>([
    { id: 0, symbol: '', percentage: '100' },
  ]);
  const [error, setError] = useState<string | null>(null);
  const [partialError, setPartialError] = useState<string | null>(null);
  const [createdPortfolio, setCreatedPortfolio] = useState<PortfolioResponse | null>(null);
  const [saving, setSaving] = useState(false);
  const totalPercentage = holdings.reduce((sum, holding) => (
    sum + (Number(holding.percentage) || 0)
  ), 0);

  function addHolding() {
    const id = nextHoldingId.current;
    nextHoldingId.current += 1;
    setHoldings(previous => [...previous, { id, symbol: '', percentage: '0' }]);
    setError(null);
  }

  function updateHolding(id: number, update: Partial<DraftHolding>) {
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

  async function savePortfolio() {
    if (saving) return;
    if (!name.trim()) {
      setError('Enter a portfolio name.');
      return;
    }

    const validationError = validateHoldings(holdings);
    if (validationError) {
      setError(validationError);
      return;
    }

    setSaving(true);
    setError(null);
    setPartialError(null);

    let target = createdPortfolio;
    if (!target) {
      try {
        target = await createPortfolio({ name: name.trim() });
        setCreatedPortfolio(target);
      } catch (requestError) {
        setError(portfolioErrorMessage(requestError, 'Unable to create portfolio.'));
        setSaving(false);
        return;
      }
    }

    try {
      const saved = await replacePortfolioHoldings(target.id, {
        holdings: holdings.map(holding => ({
          symbol: holding.symbol.trim(),
          weight: requestWeight(holding.percentage),
        })),
      });
      go(`portfolio/${saved.id}`);
    } catch (requestError) {
      setPartialError(portfolioErrorMessage(requestError, 'Unable to save portfolio holdings.'));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page create-page">
      <button className="create-back-link" onClick={() => go('portfolios')} disabled={saving}>← Back to Portfolios</button>
      <section className="create-header">
        <div><h1>Create New Portfolio</h1><p>Save a name and an ordered symbol-and-weight allocation.</p></div>
      </section>

      {partialError && createdPortfolio && (
        <div className={styles.partialSuccess} role="alert">
          <strong>Portfolio created; holdings not saved</strong>
          <p>“{createdPortfolio.name}” exists as an empty portfolio, but the separate holdings request failed: {partialError}</p>
          <div className={styles.partialActions}>
            <button className="primary-btn" onClick={() => void savePortfolio()} disabled={saving}>Retry holdings</button>
            <button className="secondary-btn" onClick={() => go(`portfolio/${createdPortfolio.id}`)} disabled={saving}>Open empty portfolio</button>
          </div>
        </div>
      )}

      {error && <p className={styles.error} role="alert">{error}</p>}

      <div className="create-workspace">
        <Card className="wizard-main">
          <div className="wizard-section-header">
            <span>PORTFOLIO RECORD</span>
            <h2>Name and Ordered Holdings</h2>
            <p>The browser creates the named portfolio first, then saves all holdings with a second request.</p>
          </div>

          <div className="wizard-step-content basic-info-step">
            <label className="wizard-field">
              <span>Portfolio Name</span><small>The backend trims and validates the final name.</small>
              <input value={name} onChange={event => { setName(event.target.value); setError(null); }} placeholder="e.g. Long-Term Growth" disabled={saving || Boolean(createdPortfolio)} />
            </label>
          </div>

          <div className="wizard-step-content holdings-step">
            <div className="wizard-title-row">
              <div><strong>Manual symbol entry</strong><p>No asset catalogue, autocomplete, price, or company metadata is used.</p></div>
              <button className="primary-btn" onClick={addHolding} disabled={saving}>＋ Add Holding</button>
            </div>
            <div className="table-scroll">
              <table className={styles.holdingTable}>
                <thead><tr><th>Order</th><th>Symbol</th><th>Allocation (%)</th><th>Actions</th></tr></thead>
                <tbody>{holdings.map((holding, index) => (
                  <tr key={holding.id}>
                    <td>{index + 1}</td>
                    <td><input aria-label={`Holding ${index + 1} symbol`} value={holding.symbol} onChange={event => updateHolding(holding.id, { symbol: event.target.value })} placeholder="e.g. AAPL" disabled={saving} /></td>
                    <td><input aria-label={`${holding.symbol || `Holding ${index + 1}`} allocation percentage`} type="number" min="0" max="100" step="0.01" value={holding.percentage} onChange={event => updateHolding(holding.id, { percentage: event.target.value })} disabled={saving} /></td>
                    <td><div className={styles.orderActions}>
                      <button aria-label={`Move holding ${index + 1} up`} onClick={() => moveHolding(index, -1)} disabled={saving || index === 0}>↑</button>
                      <button aria-label={`Move holding ${index + 1} down`} onClick={() => moveHolding(index, 1)} disabled={saving || index === holdings.length - 1}>↓</button>
                      <button className={styles.dangerButton} aria-label={`Remove holding ${index + 1}`} onClick={() => { setHoldings(previous => previous.filter(item => item.id !== holding.id)); setError(null); }} disabled={saving}>×</button>
                    </div></td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            <div className="allocation-status">
              <div><span>Total allocation</span><small>30% is sent to the backend as 0.30.</small></div>
              <div className="allocation-progress"><span style={{ width: `${Math.min(100, Math.max(0, totalPercentage))}%` }} /><b className={Math.abs(totalPercentage - 100) <= 1e-7 ? 'green-text' : 'orange-text'}>{Number(totalPercentage.toFixed(10))}%</b></div>
            </div>
          </div>

          <div className="review-holdings-card">
            <div className="review-holdings-title"><h3>Request Review</h3></div>
            <div className={styles.metadataGrid}>
              <div><small>Name</small><strong>{name.trim() || 'Missing name'}</strong></div>
              <div><small>Holdings</small><strong>{holdings.length}</strong></div>
              <div><small>Allocation</small><strong>{Number(totalPercentage.toFixed(10))}%</strong></div>
            </div>
          </div>

          <div className="educational-notice"><Icon name="shield" size={19} /><p>Only the name, ordered symbols, and decimal weights are persisted. Aura does not infer prices, shares, values, or asset metadata here.</p></div>

          <div className="wizard-footer">
            <button className="secondary-btn" onClick={() => go('portfolios')} disabled={saving}>Cancel</button>
            <button className="primary-btn create-confirm-btn" onClick={() => void savePortfolio()} disabled={saving}>
              {saving ? 'Saving…' : createdPortfolio ? 'Retry Holdings' : 'Create Portfolio'} <span>✓</span>
            </button>
          </div>
        </Card>

        <aside className="create-sidebar">
          <Card className="after-create-card">
            <h3>Two backend operations</h3>
            <div><span>1</span><p><strong>Create portfolio</strong><small>POST saves the named empty portfolio.</small></p></div>
            <div><span>2</span><p><strong>Save holdings</strong><small>PUT replaces the complete ordered allocation.</small></p></div>
          </Card>
        </aside>
      </div>
    </div>
  );
}
