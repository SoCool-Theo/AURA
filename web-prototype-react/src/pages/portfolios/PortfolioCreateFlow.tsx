import { useRef, useState } from 'react';
import {
  createPortfolio,
  replacePlannedPortfolioHoldings,
  replaceRealPortfolioHoldings,
} from '../../api/portfoliosApi';
import { go } from '../../app/routes';
import { FormErrorSummary } from '../../components/ui/ApiErrorState';
import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import type {
  PortfolioCurrency,
  PortfolioPlannedHoldingInput,
  PortfolioRealHoldingInput,
  PortfolioResponse,
} from '../../types/portfolio';
import styles from './PortfolioIntegration.module.css';
import {
  createPlannedHoldingDraft,
  createRealHoldingDraft,
  type PlannedHoldingDraft,
  type RealHoldingDraft,
  validatePlannedHoldingDrafts,
  validateRealHoldingDrafts,
} from './portfolioValidation';
import { AssetSymbolField } from './components/AssetSymbolField';

type CreateMode = 'CURRENT' | 'PLANNED';
type DraftHolding = RealHoldingDraft | PlannedHoldingDraft;

function todayInputValue(): string {
  const today = new Date();
  return [
    today.getFullYear(),
    String(today.getMonth() + 1).padStart(2, '0'),
    String(today.getDate()).padStart(2, '0'),
  ].join('-');
}

export function PortfolioCreateFlow() {
  const nextHoldingId = useRef(1);
  const [name, setName] = useState('');
  const [mode, setMode] = useState<CreateMode>('CURRENT');
  const [planCurrency, setPlanCurrency] = useState<PortfolioCurrency>('USD');
  const [holdings, setHoldings] = useState<DraftHolding[]>([
    createRealHoldingDraft(0),
  ]);
  const [error, setError] = useState<unknown>(null);
  const [partialError, setPartialError] = useState<unknown>(null);
  const [createdPortfolio, setCreatedPortfolio] = useState<PortfolioResponse | null>(null);
  const [saving, setSaving] = useState(false);
  const maximumPurchaseDate = todayInputValue();

  function addHolding() {
    const id = nextHoldingId.current;
    nextHoldingId.current += 1;
    setHoldings(previous => [
      ...previous,
      mode === 'PLANNED'
        ? createPlannedHoldingDraft(id)
        : createRealHoldingDraft(id),
    ]);
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

  function selectMode(nextMode: CreateMode) {
    if (nextMode === mode || saving || createdPortfolio) return;
    setMode(nextMode);
    setHoldings([
      nextMode === 'PLANNED'
        ? createPlannedHoldingDraft(0)
        : createRealHoldingDraft(0),
    ]);
    nextHoldingId.current = 1;
    setError(null);
    setPartialError(null);
  }

  async function savePortfolio() {
    if (saving) return;
    if (!name.trim()) {
      setError('Enter a portfolio name.');
      return;
    }

    const validation = mode === 'PLANNED'
      ? validatePlannedHoldingDrafts(holdings as PlannedHoldingDraft[])
      : validateRealHoldingDrafts(holdings as RealHoldingDraft[]);
    if (!validation.holdings) {
      setError(validation.error);
      return;
    }

    setSaving(true);
    setError(null);
    setPartialError(null);

    let target = createdPortfolio;
    if (!target) {
      try {
        target = await createPortfolio(mode === 'PLANNED'
          ? {
            name: name.trim(),
            portfolio_type: 'PLANNED',
            plan_currency: planCurrency,
          }
          : {
            name: name.trim(),
            portfolio_type: 'CURRENT',
          });
        setCreatedPortfolio(target);
      } catch (requestError) {
        setError(requestError);
        setSaving(false);
        return;
      }
    }

    try {
      const saved = mode === 'PLANNED'
        ? await replacePlannedPortfolioHoldings(
          target.id,
          validation.holdings as PortfolioPlannedHoldingInput[],
        )
        : await replaceRealPortfolioHoldings(
          target.id,
          validation.holdings as PortfolioRealHoldingInput[],
        );
      go(`portfolio/${saved.id}`);
    } catch (requestError) {
      setPartialError(requestError);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page create-page">
      <button className="create-back-link" onClick={() => go('portfolios')} disabled={saving}>← Back to Portfolios</button>
      <section className="create-header">
        <div>
          <h1>Create New Portfolio</h1>
          <p>{mode === 'PLANNED'
            ? 'Model a proposed investment before you invest.'
            : 'Record investments you already own.'}</p>
        </div>
      </section>

      {Boolean(partialError) && createdPortfolio && (
        <div className={styles.partialSuccess} role="alert">
          <strong>Portfolio created; holdings still need attention</strong>
          <p>“{createdPortfolio.name}” was created, but its holdings could not be saved.</p>
          <FormErrorSummary error={partialError} message="Review the holdings and retry saving them." />
          <div className={styles.partialActions}>
            <button className="primary-btn" onClick={() => void savePortfolio()} disabled={saving}>Retry holdings</button>
            <button className="secondary-btn" onClick={() => go(`portfolio/${createdPortfolio.id}`)} disabled={saving}>Open empty portfolio</button>
          </div>
        </div>
      )}

      {Boolean(error) && <FormErrorSummary error={error} />}

      <div className="create-workspace">
        <Card className="wizard-main">
          <div className="wizard-section-header">
            <span>PORTFOLIO SETUP</span>
            <h2>Name and Holdings</h2>
            <p>Choose whether you are analyzing investments you own or a plan you are considering.</p>
          </div>

          <div className="wizard-step-content basic-info-step">
            <label className="wizard-field">
              <span>Portfolio Name</span><small>Choose a clear name you will recognize later.</small>
              <input value={name} onChange={event => { setName(event.target.value); setError(null); }} placeholder="e.g. Long-Term Growth" disabled={saving || Boolean(createdPortfolio)} />
            </label>
          </div>

          <fieldset className={styles.modeFieldset} disabled={saving || Boolean(createdPortfolio)}>
            <legend>What would you like to analyze?</legend>
            <div className={styles.modeSelector}>
              <button
                type="button"
                className={mode === 'CURRENT' ? styles.modeSelected : ''}
                aria-pressed={mode === 'CURRENT'}
                onClick={() => selectMode('CURRENT')}
              >
                <strong>My Current Portfolio</strong>
                <span>I already own these investments.</span>
              </button>
              <button
                type="button"
                className={mode === 'PLANNED' ? styles.modeSelected : ''}
                aria-pressed={mode === 'PLANNED'}
                onClick={() => selectMode('PLANNED')}
              >
                <strong>A Planned Portfolio</strong>
                <span>I want to evaluate amounts before investing.</span>
              </button>
            </div>
          </fieldset>

          {mode === 'PLANNED' && (
            <fieldset className={styles.currencyFieldset} disabled={saving || Boolean(createdPortfolio)}>
              <legend>Plan currency</legend>
              <div className={styles.currencySelector}>
                {(['USD', 'THB'] as PortfolioCurrency[]).map(currency => (
                  <button
                    type="button"
                    key={currency}
                    className={planCurrency === currency ? styles.currencySelected : ''}
                    aria-pressed={planCurrency === currency}
                    onClick={() => setPlanCurrency(currency)}
                  >{currency}</button>
                ))}
              </div>
            </fieldset>
          )}

          <div className="wizard-step-content holdings-step">
            <div className="wizard-title-row">
              <div><strong>Holdings</strong><p>Add each asset in the order you want it displayed.</p></div>
              <button className="primary-btn" onClick={addHolding} disabled={saving}>＋ Add Holding</button>
            </div>
            <div className="table-scroll">
              <table className={styles.holdingTable}>
                <thead><tr>
                  <th>Order</th>
                  <th>Symbol</th>
                  {mode === 'PLANNED' ? (
                    <th>Proposed Amount ({planCurrency})</th>
                  ) : <>
                    <th>Invested Amount</th>
                    <th>Currency</th>
                    <th>Shares Owned</th>
                    <th>Purchase Date</th>
                  </>}
                  <th>Actions</th>
                </tr></thead>
                <tbody>{holdings.map((holding, index) => (
                  <tr key={holding.id}>
                    <td>{index + 1}</td>
                    <td><AssetSymbolField ariaLabel={`Holding ${index + 1} symbol`} id={`create-holding-${holding.id}`} value={holding.symbol} onChange={symbol => updateHolding(holding.id, { symbol })} disabled={saving} /></td>
                    {mode === 'PLANNED' && 'proposedAmount' in holding ? (
                      <td><input aria-label={`${holding.symbol || `Holding ${index + 1}`} proposed amount`} inputMode="decimal" value={holding.proposedAmount} onChange={event => updateHolding(holding.id, { proposedAmount: event.target.value })} placeholder="4000.00" disabled={saving} /></td>
                    ) : 'investedAmount' in holding ? <>
                      <td><input aria-label={`${holding.symbol || `Holding ${index + 1}`} invested amount`} inputMode="decimal" value={holding.investedAmount} onChange={event => updateHolding(holding.id, { investedAmount: event.target.value })} placeholder="1000.00" disabled={saving} /></td>
                      <td>
                        <select aria-label={`${holding.symbol || `Holding ${index + 1}`} invested currency`} value={holding.investedCurrency} onChange={event => updateHolding(holding.id, { investedCurrency: event.target.value as PortfolioCurrency })} disabled={saving}>
                          <option value="USD">USD</option>
                          <option value="THB">THB</option>
                        </select>
                      </td>
                      <td><input aria-label={`${holding.symbol || `Holding ${index + 1}`} shares owned`} inputMode="decimal" value={holding.shares} onChange={event => updateHolding(holding.id, { shares: event.target.value })} placeholder="10.5" disabled={saving} /></td>
                      <td>
                        <label className={styles.dateField}>
                          <span className="sr-only">{holding.symbol || `Holding ${index + 1}`} purchase date</span>
                          <input aria-label={`${holding.symbol || `Holding ${index + 1}`} purchase date`} type="date" max={maximumPurchaseDate} value={holding.purchaseDate} onChange={event => updateHolding(holding.id, { purchaseDate: event.target.value })} disabled={saving} />
                          <Icon name="calendar" size={17} />
                        </label>
                      </td>
                    </> : null}
                    <td><div className={styles.orderActions}>
                      <button aria-label={`Move holding ${index + 1} up`} onClick={() => moveHolding(index, -1)} disabled={saving || index === 0}>↑</button>
                      <button aria-label={`Move holding ${index + 1} down`} onClick={() => moveHolding(index, 1)} disabled={saving || index === holdings.length - 1}>↓</button>
                      <button className={styles.dangerButton} aria-label={`Remove holding ${index + 1}`} onClick={() => { setHoldings(previous => previous.filter(item => item.id !== holding.id)); setError(null); }} disabled={saving}>×</button>
                    </div></td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </div>

          <div className="review-holdings-card">
            <div className="review-holdings-title"><h3>Request Review</h3></div>
            <div className={styles.metadataGrid}>
              <div><small>Name</small><strong>{name.trim() || 'Missing name'}</strong></div>
              <div><small>Type</small><strong>{mode === 'PLANNED' ? 'Planned portfolio' : 'Current portfolio'}</strong></div>
              <div><small>Holdings</small><strong>{holdings.length}</strong></div>
              <div><small>Allocation</small><strong>Calculated automatically</strong></div>
            </div>
          </div>

          <div className="educational-notice"><Icon name="spark" size={19} /><p>{mode === 'PLANNED'
            ? 'Aura calculates target percentages from your proposed amounts. Estimated shares are for display only and do not control the analysis.'
            : 'Aura uses market prices to value your shares and calculate the current percentage of each holding.'}</p></div>

          <div className="wizard-footer">
            <button className="secondary-btn" onClick={() => go('portfolios')} disabled={saving}>Cancel</button>
            <button className="primary-btn create-confirm-btn" onClick={() => void savePortfolio()} disabled={saving}>
              {saving ? 'Saving…' : createdPortfolio ? 'Retry Holdings' : 'Create Portfolio'} <span>✓</span>
            </button>
          </div>
        </Card>

        <aside className="create-sidebar">
          <Card className="after-create-card">
            <h3>{mode === 'PLANNED' ? 'Planned portfolio' : 'Current portfolio'}</h3>
            {mode === 'PLANNED' ? <>
              <div><span>1</span><p><strong>Enter proposed amounts</strong><small>Use one currency for the complete plan.</small></p></div>
              <div><span>2</span><p><strong>Review historical risk</strong><small>The plan remains hypothetical and is not an order.</small></p></div>
            </> : <>
              <div><span>1</span><p><strong>Record what you own</strong><small>Add actual shares and transaction details.</small></p></div>
              <div><span>2</span><p><strong>See current allocation</strong><small>Aura values the holdings using available market data.</small></p></div>
            </>}
          </Card>
        </aside>
      </div>
    </div>
  );
}
