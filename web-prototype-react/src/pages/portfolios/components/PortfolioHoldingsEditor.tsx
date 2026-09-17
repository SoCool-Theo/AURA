import { useEffect, useRef, useState } from 'react';
import {
  replacePlannedPortfolioHoldings,
  replaceRealPortfolioHoldings,
} from '../../../api/portfoliosApi';
import { FormErrorSummary } from '../../../components/ui/ApiErrorState';
import { Card } from '../../../components/ui/Card';
import {
  isPlannedPortfolioHolding,
  isRealPortfolioHolding,
  portfolioHoldingMode,
  type PortfolioHoldingMode,
  type PortfolioPlannedHoldingInput,
  type PortfolioRealHoldingInput,
  type PortfolioResponse,
} from '../../../types/portfolio';
import styles from '../PortfolioIntegration.module.css';
import {
  createPlannedHoldingDraft,
  createRealHoldingDraft,
  plannedHoldingToDraft,
  realHoldingToDraft,
  type PlannedHoldingDraft,
  type RealHoldingDraft,
  validatePlannedHoldingDrafts,
  validateRealHoldingDrafts,
} from '../portfolioValidation';
import { AssetSymbolField } from './AssetSymbolField';

type EditableHolding = RealHoldingDraft | PlannedHoldingDraft;

function editorMode(portfolio: PortfolioResponse): PortfolioHoldingMode {
  if (portfolio.portfolio_type === 'PLANNED') return 'planned';
  if (portfolio.portfolio_type === 'LEGACY') return 'legacy';
  const detected = portfolioHoldingMode(portfolio.holdings);
  return detected === 'empty' ? 'real' : detected;
}

function editableHoldings(portfolio: PortfolioResponse): EditableHolding[] {
  const planned = portfolio.portfolio_type === 'PLANNED';
  const rows = portfolio.holdings.map((holding, index) => {
    if (planned && isPlannedPortfolioHolding(holding)) {
      return plannedHoldingToDraft(index, holding);
    }
    if (!planned && isRealPortfolioHolding(holding)) {
      return realHoldingToDraft(index, holding);
    }

    const draft = planned
      ? createPlannedHoldingDraft(index)
      : createRealHoldingDraft(index);
    draft.symbol = holding.symbol;
    return draft;
  });

  if (!rows.length) {
    rows.push(planned
      ? createPlannedHoldingDraft(0)
      : createRealHoldingDraft(0));
  }
  return rows;
}

type PortfolioHoldingsEditorProps = {
  portfolio: PortfolioResponse;
  onSaved: (portfolio: PortfolioResponse) => void;
};

export function PortfolioHoldingsEditor({
  portfolio,
  onSaved,
}: PortfolioHoldingsEditorProps) {
  const mode = editorMode(portfolio);
  const planned = mode === 'planned';
  const nextId = useRef(portfolio.holdings.length || 1);
  const [holdings, setHoldings] = useState(() => editableHoldings(portfolio));
  const [error, setError] = useState<unknown>(null);
  const [saving, setSaving] = useState(false);

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
    if (saving) return;
    const validation = planned
      ? validatePlannedHoldingDrafts(holdings as PlannedHoldingDraft[])
      : validateRealHoldingDrafts(holdings as RealHoldingDraft[]);
    if (!validation.holdings) {
      setError(validation.error);
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const updated = planned
        ? await replacePlannedPortfolioHoldings(
          portfolio.id,
          validation.holdings as PortfolioPlannedHoldingInput[],
        )
        : await replaceRealPortfolioHoldings(
          portfolio.id,
          validation.holdings as PortfolioRealHoldingInput[],
        );
      onSaved(updated);
    } catch (requestError) {
      setError(requestError);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="detail-tab-panel">
      <Card className="detail-section-card">
        <div className="detail-section-header">
          <div>
            <h2>{planned ? 'Edit Planned Holdings' : 'Edit Current Holdings'}</h2>
            <p>{planned
              ? `Update the complete ordered list of proposed investments in ${portfolio.plan_currency ?? 'USD'}.`
              : 'Update the complete ordered list of assets and quantities you own.'}</p>
          </div>
          <div className={styles.portfolioTypeBadge}>{planned ? 'Planned' : 'Current'}</div>
        </div>

        {mode === 'legacy' && (
          <div className={styles.conversionNotice} role="note">
            <strong>Convert legacy allocation</strong>
            <p>Enter the quantity owned for every saved symbol. Saving replaces the old manual percentages with quantity-based current holdings.</p>
          </div>
        )}

        {mode === 'mixed' && (
          <div className={styles.conversionNotice} role="alert">
            <strong>Holding details need correction</strong>
            <p>Enter a valid quantity owned for every symbol before saving.</p>
          </div>
        )}

        {Boolean(error) && <FormErrorSummary error={error} />}

        <div className="table-scroll">
          <table className={styles.holdingTable}>
            <thead><tr>
              <th>Order</th>
              <th>Symbol</th>
              {planned ? (
                <th>Proposed Amount ({portfolio.plan_currency ?? 'USD'})</th>
              ) : <th>Quantity Owned</th>}
              <th>Actions</th>
            </tr></thead>
            <tbody>{holdings.map((holding, index) => (
              <tr key={holding.id}>
                <td>{index + 1}</td>
                <td><AssetSymbolField ariaLabel={`Holding ${index + 1} symbol`} id={`edit-holding-${holding.id}`} value={holding.symbol} onChange={symbol => updateHolding(holding.id, { symbol })} disabled={saving} /></td>
                {planned && 'proposedAmount' in holding ? (
                  <td><input aria-label={`${holding.symbol || `Holding ${index + 1}`} proposed amount`} inputMode="decimal" value={holding.proposedAmount} onChange={event => updateHolding(holding.id, { proposedAmount: event.target.value })} placeholder="4000.00" disabled={saving} /></td>
                ) : 'shares' in holding ? (
                  <td><input aria-label={`${holding.symbol || `Holding ${index + 1}`} quantity owned`} inputMode="decimal" value={holding.shares} onChange={event => updateHolding(holding.id, { shares: event.target.value })} placeholder="10.5" disabled={saving} /></td>
                ) : null}
                <td><div className={styles.orderActions}>
                  <button aria-label={`Move holding ${index + 1} up`} onClick={() => moveHolding(index, -1)} disabled={saving || index === 0}>↑</button>
                  <button aria-label={`Move holding ${index + 1} down`} onClick={() => moveHolding(index, 1)} disabled={saving || index === holdings.length - 1}>↓</button>
                  <button className={styles.dangerButton} aria-label={`Remove holding ${index + 1}`} onClick={() => { setHoldings(previous => previous.filter(item => item.id !== holding.id)); setError(null); }} disabled={saving}>×</button>
                </div></td>
              </tr>
            ))}</tbody>
          </table>
        </div>

        <div className="detail-section-footer">
          <p>{planned
            ? 'Target allocation is calculated automatically from the proposed amounts. Estimated shares are display-only.'
            : 'Current value and allocation are calculated automatically from the saved quantity and backend market prices.'}</p>
          <div className={styles.editorActions}>
            <button className="secondary-btn" disabled={saving} onClick={() => {
              const id = nextId.current;
              nextId.current += 1;
              setHoldings(previous => [
                ...previous,
                planned
                  ? createPlannedHoldingDraft(id)
                  : createRealHoldingDraft(id),
              ]);
              setError(null);
            }}>＋ Add holding</button>
            <button className="primary-btn" onClick={() => void save()} disabled={saving}>{saving
              ? 'Saving…'
              : planned
                ? 'Save Planned Holdings'
                : mode === 'legacy'
                  ? 'Convert and Save Holdings'
                  : 'Save Current Holdings'}</button>
          </div>
        </div>
      </Card>
    </div>
  );
}
