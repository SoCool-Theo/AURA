import { Fragment, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import type { Holding, Portfolio } from '../../types/portfolio';
import { go } from '../../app/routes';
import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import { SymbolBadge } from '../../components/ui/SymbolBadge';
import { money } from '../../utils/formatting';
import { slug } from '../../utils/uiCalculations';

type DraftHolding = Omit<Holding, 'value' | 'dailyChange'>;

interface CreatePortfolioPageProps {
  portfolios: Portfolio[];
  setPortfolios: Dispatch<SetStateAction<Portfolio[]>>;
}

const STEPS = [
  ['1', 'Basic Info', 'Name and preferences'],
  ['2', 'Add Holdings', 'Build your allocation'],
  ['3', 'Review', 'Confirm and create'],
];

const INITIAL_HOLDINGS: DraftHolding[] = [
  { symbol: 'NVDA', name: 'NVIDIA Corporation', type: 'Equity', price: 181.63, shares: 58, weight: 57.1 },
  { symbol: 'TSLA', name: 'Tesla, Inc.', type: 'Equity', price: 177.74, shares: 15, weight: 14.4 },
  { symbol: 'AAPL', name: 'Apple Inc.', type: 'Equity', price: 191.45, shares: 10, weight: 10.4 },
  { symbol: 'BND', name: 'Vanguard Total Bond Market ETF', type: 'Bond', price: 72.16, shares: 40, weight: 15.4 },
  { symbol: 'CASH', name: 'Cash', type: 'Cash', price: 1, shares: 484.9, weight: 2.7 },
];

function HoldingsReview({ holdings }: { holdings: DraftHolding[] }) {
  return (
    <div className="holding-review">
      {holdings.map(holding => (
        <div key={holding.symbol}>
          <div className="asset-cell">
            <SymbolBadge symbol={holding.symbol} />
            <div><strong>{holding.symbol}</strong><small>{holding.name}</small></div>
          </div>
          <strong>{holding.weight}%</strong>
          <span>{money(holding.price * holding.shares)}</span>
        </div>
      ))}
    </div>
  );
}

export function CreatePortfolioPage({ portfolios, setPortfolios }: CreatePortfolioPageProps) {
  const [step, setStep] = useState(1);
  const [name, setName] = useState('My New Portfolio');
  const [description, setDescription] = useState('My long term investment portfolio.');
  const [holdings, setHoldings] = useState<DraftHolding[]>(INITIAL_HOLDINGS);
  const total = holdings.reduce((sum, holding) => sum + holding.price * holding.shares, 0);
  const totalWeight = holdings.reduce((sum, holding) => sum + Number(holding.weight), 0);
  const currentStep = STEPS[step - 1];

  function addHolding() {
    const symbol = prompt('Asset symbol');
    if (!symbol) return;
    const amount = Number(prompt('Amount invested in USD', '1000')) || 1000;
    const price = 100;
    const newHolding: DraftHolding = {
      symbol: symbol.toUpperCase(),
      name: `${symbol.toUpperCase()} Asset`,
      type: 'Equity',
      price,
      shares: amount / price,
      weight: 0,
    };
    const next = [...holdings, newHolding];
    const nextTotal = next.reduce((sum, holding) => sum + holding.price * holding.shares, 0);
    setHoldings(next.map(holding => ({
      ...holding,
      weight: Number(((holding.price * holding.shares / nextTotal) * 100).toFixed(1)),
    })));
  }

  function removeHolding(symbol: string) {
    const next = holdings.filter(holding => holding.symbol !== symbol);
    const nextTotal = next.reduce((sum, holding) => sum + holding.price * holding.shares, 0);
    setHoldings(next.map(holding => ({
      ...holding,
      weight: Number(((holding.price * holding.shares / nextTotal) * 100).toFixed(1)),
    })));
  }

  function create() {
    if (!name.trim()) return alert('Please enter a portfolio name.');
    if (!holdings.length) return alert('Add at least one holding.');

    const id = `${slug(name)}-${Date.now()}`;
    const value = holdings.reduce((sum, holding) => sum + holding.price * holding.shares, 0);
    const cashHolding = holdings.find(holding => holding.symbol === 'CASH');
    const portfolio: Portfolio = {
      id,
      name: name.trim(),
      created: new Date().toISOString().slice(0, 10),
      value,
      totalReturn: 0,
      riskScore: 55,
      riskLevel: 'Moderate',
      cash: cashHolding ? cashHolding.price * cashHolding.shares : 0,
      holdings: holdings.map(holding => ({
        ...holding,
        value: holding.price * holding.shares,
        dailyChange: 0,
      })),
    };
    setPortfolios([...portfolios, portfolio]);
    go(`portfolio/${id}`);
  }

  return (
    <div className="page create-page">
      <button className="create-back-link" onClick={() => go('portfolios')}>← Back to Portfolios</button>
      <section className="create-header">
        <div><h1>Create New Portfolio</h1><p>Build a portfolio to explore its historical performance and risk.</p></div>
        <span>Step {step} of {STEPS.length}</span>
      </section>

      <Card className="create-stepper">
        {STEPS.map(([number, label, detail], index) => (
          <Fragment key={number}>
            <button
              className={`${step === Number(number) ? 'active' : ''} ${step > Number(number) ? 'complete' : ''}`}
              onClick={() => setStep(Number(number))}
              aria-current={step === Number(number) ? 'step' : undefined}
            >
              <span className="step-number">{step > Number(number) ? '✓' : number}</span>
              <span className="step-copy"><strong>{label}</strong><small>{detail}</small></span>
            </button>
            {index < STEPS.length - 1 && <span className={`step-connector ${step > index + 1 ? 'complete' : ''}`} />}
          </Fragment>
        ))}
      </Card>

      <div className="create-workspace">
        <Card className="wizard-main">
          <div className="wizard-section-header">
            <span>STEP {currentStep[0]}</span>
            <h2>{step === 1 ? 'Portfolio Information' : step === 2 ? 'Add Your Holdings' : 'Review Your Portfolio'}</h2>
            <p>{step === 1 ? 'Give this portfolio a clear name and description.' : step === 2 ? 'Add the assets and amounts you want Aura to analyze.' : 'Check the portfolio details before creating it.'}</p>
          </div>

          {step === 1 && (
            <div className="wizard-step-content basic-info-step">
              <div className="wizard-form-grid">
                <label className="wizard-field">
                  <span>Portfolio Name</span><small>Use a name that helps you recognize this portfolio.</small>
                  <input value={name} onChange={event => setName(event.target.value)} placeholder="e.g. Long-Term Growth" />
                </label>
                <label className="wizard-field">
                  <span>Currency</span><small>Values and reports will use this currency.</small>
                  <span className="wizard-select"><select><option>USD - US Dollar</option></select><Icon name="chevron-down" size={16} /></span>
                </label>
                <label className="wizard-field full">
                  <span>Description <em>Optional</em></span><small>Add a short note about the portfolio's purpose.</small>
                  <textarea rows={5} value={description} onChange={event => setDescription(event.target.value)} placeholder="Describe your investment goal..." />
                </label>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="wizard-step-content holdings-step">
              <div className="wizard-title-row">
                <label className="asset-search"><Icon name="search" size={18} /><span className="sr-only">Search assets</span><input placeholder="Search assets by symbol or company name..." /></label>
                <button className="primary-btn" onClick={addHolding}>＋ Add Manually</button>
              </div>
              <div className="wizard-holdings-table table-scroll">
                <table>
                  <thead><tr><th>Asset</th><th>Type</th><th>Price</th><th>Shares / Amount</th><th>Allocation</th><th><span className="sr-only">Action</span></th></tr></thead>
                  <tbody>{holdings.map(holding => (
                    <tr key={holding.symbol}>
                      <td><div className="asset-cell"><SymbolBadge symbol={holding.symbol} /><div><strong>{holding.symbol}</strong><small>{holding.name}</small></div></div></td>
                      <td><span className="asset-type">{holding.type}</span></td>
                      <td>{money(holding.price)}</td>
                      <td><input className="table-input" aria-label={`${holding.symbol} shares`} type="number" value={holding.shares} onChange={event => setHoldings(holdings.map(item => item.symbol === holding.symbol ? { ...item, shares: Number(event.target.value) } : item))} /></td>
                      <td><strong>{holding.weight}%</strong></td>
                      <td><button className="remove-holding" aria-label={`Remove ${holding.symbol}`} onClick={() => removeHolding(holding.symbol)}>×</button></td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
              <div className="allocation-status">
                <div><span>Total allocation</span><small>Portfolio weights should total 100%.</small></div>
                <div className="allocation-progress"><span style={{ width: `${Math.min(100, totalWeight)}%` }} /><b className={Math.abs(totalWeight - 100) < .2 ? 'green-text' : 'orange-text'}>{totalWeight.toFixed(1)}%</b></div>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="wizard-step-content review-step">
              <div className="review-summary">
                <div><small>Portfolio Name</small><strong>{name}</strong></div>
                <div><small>Total Value</small><strong>{money(total)}</strong></div>
                <div><small>Holdings</small><strong>{holdings.length}</strong></div>
                <div><small>Allocation</small><strong className={Math.abs(totalWeight - 100) < .2 ? 'green-text' : 'orange-text'}>{totalWeight.toFixed(1)}%</strong></div>
              </div>
              <div className="review-holdings-card">
                <div className="review-holdings-title"><h3>Holdings</h3><button onClick={() => setStep(2)}>Edit holdings</button></div>
                <HoldingsReview holdings={holdings} />
              </div>
              <div className="educational-notice"><Icon name="shield" size={19} /><p>Aura analyzes historical portfolio risk for educational purposes. It does not provide buy or sell recommendations.</p></div>
            </div>
          )}

          <div className="wizard-footer">
            <button className="secondary-btn" onClick={() => step === 1 ? go('portfolios') : setStep(step - 1)}>{step === 1 ? 'Cancel' : '← Back'}</button>
            {step < 3
              ? <button className="primary-btn" onClick={() => setStep(step + 1)}>{step === 1 ? 'Continue to Holdings' : 'Review Portfolio'} <span>→</span></button>
              : <button className="primary-btn create-confirm-btn" onClick={create}>Create Portfolio <span>✓</span></button>}
          </div>
        </Card>

        <aside className="create-sidebar">
          <Card className="portfolio-preview-card">
            <div className="preview-icon"><Icon name="portfolios" size={22} /></div>
            <small>PORTFOLIO PREVIEW</small><h3>{name.trim() || 'Untitled Portfolio'}</h3><p>{description.trim() || 'No description added.'}</p>
            <dl><div><dt>Estimated value</dt><dd>{money(total)}</dd></div><div><dt>Holdings</dt><dd>{holdings.length}</dd></div><div><dt>Allocation</dt><dd className={Math.abs(totalWeight - 100) < .2 ? 'green-text' : 'orange-text'}>{totalWeight.toFixed(1)}%</dd></div></dl>
          </Card>
          <Card className="after-create-card">
            <h3>What happens next?</h3>
            <div><span>1</span><p><strong>Create portfolio</strong><small>Save these holdings in your Aura workspace.</small></p></div>
            <div><span>2</span><p><strong>Run analysis</strong><small>Calculate historical risk and performance metrics.</small></p></div>
            <div><span>3</span><p><strong>Explore insights</strong><small>Understand the results in beginner-friendly language.</small></p></div>
          </Card>
        </aside>
      </div>
    </div>
  );
}
