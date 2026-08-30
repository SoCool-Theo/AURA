import type { PortfolioSummaryResponse } from '../../../types/portfolio';
import type { HistoricalScenarioResponse, SimulationMode } from '../../../types/simulation';
import { go } from '../../../app/routes';
import { Card } from '../../../components/ui/Card';
import { HistoricalScenarioSelector } from './HistoricalScenarioSelector';
import styles from '../SimulationIntegration.module.css';

interface Props { portfolios: PortfolioSummaryResponse[]; portfolioId: string; mode: SimulationMode; scenarios: HistoricalScenarioResponse[]; scenarioId: string; startDate: string; endDate: string; loading: boolean; running: boolean; onScenarioChange: (id: string) => void; onStartDateChange: (value: string) => void; onEndDateChange: (value: string) => void; onRun: () => void }

export function SimulationSetup(props: Props) {
  return <Card className="simulation-setup-card">
    <div className="simulation-setup-heading"><div><span>SIMULATION SETUP</span><h2>Configure your test</h2></div><small>Historical results are educational, not predictive.</small></div>
    <div className="simulation-controls-grid">
      <label className="simulation-control-field"><span>Portfolio</span><small>Owner-scoped saved portfolio</small><select className={styles.portfolioSelect} value={props.portfolioId} onChange={event => go(`simulations/${event.target.value}`)} disabled={props.loading || props.running}><option value="" disabled>{props.portfolios.length ? 'Select a portfolio' : 'No portfolios available'}</option>{props.portfolios.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      {props.mode === 'allocation' ? <div className={styles.dateFields}><label>Requested start date<input type="date" value={props.startDate} onChange={event => props.onStartDateChange(event.target.value)} disabled={props.running} /></label><label>Requested end date<input type="date" value={props.endDate} onChange={event => props.onEndDateChange(event.target.value)} disabled={props.running} /></label></div> : <HistoricalScenarioSelector scenarios={props.scenarios} scenarioId={props.scenarioId} onChange={props.onScenarioChange} loading={props.loading} disabled={props.running} />}
      <button className="primary-btn run-simulation-btn" onClick={props.onRun} disabled={props.loading || props.running || !props.portfolioId}><span>▶</span> {props.running ? 'Running…' : 'Run Simulation'}</button>
    </div>
  </Card>;
}
