import type { PortfolioSummaryResponse } from '../../../types/portfolio';
import type { HistoricalScenarioResponse, SimulationMode } from '../../../types/simulation';
import { go } from '../../../app/routes';
import { AuraSelect } from '../../../components/ui/AuraSelect';
import type { AuraSelectOption } from '../../../components/ui/AuraSelect';
import { Card } from '../../../components/ui/Card';
import { HistoricalScenarioSelector } from './HistoricalScenarioSelector';
import styles from '../SimulationIntegration.module.css';

interface Props { portfolios: PortfolioSummaryResponse[]; portfolioId: string; mode: SimulationMode; scenarios: HistoricalScenarioResponse[]; scenarioId: string; startDate: string; endDate: string; loading: boolean; running: boolean; onScenarioChange: (id: string) => void; onStartDateChange: (value: string) => void; onEndDateChange: (value: string) => void; onRun: () => void }

export function SimulationSetup(props: Props) {
  const portfolioOptions: AuraSelectOption<string>[] = [
    {
      value: '',
      label: props.loading
        ? 'Loading portfolios…'
        : props.portfolios.length
          ? 'Select a portfolio'
          : 'No portfolios available',
      description: 'Choose a saved portfolio',
      icon: 'wallet',
      tone: 'neutral',
      disabled: true,
    },
    ...props.portfolios.map(portfolio => ({
      value: portfolio.id,
      label: portfolio.name,
      description: portfolio.portfolio_type === 'PLANNED'
        ? `Planned allocation · ${portfolio.plan_currency ?? 'USD'}`
        : portfolio.portfolio_type === 'LEGACY'
          ? 'Legacy saved allocation'
          : 'Current holdings',
      icon: 'wallet',
      tone: 'teal' as const,
    })),
  ];

  return <Card className="simulation-setup-card">
    <div className="simulation-setup-heading"><div><span>SIMULATION SETUP</span><h2>Configure your test</h2></div><small>Historical results are educational, not predictive.</small></div>
    <div className="simulation-controls-grid">
      <div className="simulation-control-field"><span>Portfolio</span><small>Choose current holdings, a planned allocation, or a legacy portfolio</small><AuraSelect className={styles.portfolioSelect} ariaLabel="Select portfolio for simulation" value={props.portfolioId} options={portfolioOptions} onChange={nextPortfolioId => go(`simulations/${nextPortfolioId}`)} disabled={props.loading || props.running} /></div>
      {props.mode === 'allocation' ? <div className={styles.dateFields}><label>Requested start date<input type="date" value={props.startDate} onChange={event => props.onStartDateChange(event.target.value)} disabled={props.running} /></label><label>Requested end date<input type="date" value={props.endDate} onChange={event => props.onEndDateChange(event.target.value)} disabled={props.running} /></label></div> : <HistoricalScenarioSelector scenarios={props.scenarios} scenarioId={props.scenarioId} onChange={props.onScenarioChange} loading={props.loading} disabled={props.running} />}
      <button className="primary-btn run-simulation-btn" onClick={props.onRun} disabled={props.loading || props.running || !props.portfolioId}><span>▶</span> {props.running ? 'Running…' : 'Run Simulation'}</button>
    </div>
  </Card>;
}
