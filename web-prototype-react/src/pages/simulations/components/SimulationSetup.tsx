import type { Portfolio } from '../../../types/portfolio';
import { go } from '../../../app/routes';
import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';
import { HistoricalScenarioSelector } from './HistoricalScenarioSelector';

interface SimulationSetupProps {
  portfolio: Portfolio;
  scenarioId: string;
  onScenarioChange: (scenarioId: string) => void;
  onRun: () => void;
}

export function SimulationSetup({
  portfolio,
  scenarioId,
  onScenarioChange,
  onRun,
}: SimulationSetupProps) {
  return (
    <Card className="simulation-setup-card">
      <div className="simulation-setup-heading">
        <div><span>SIMULATION SETUP</span><h2>Configure your test</h2></div>
        <small>Historical results are educational, not predictive.</small>
      </div>
      <div className="simulation-controls-grid">
        <label>
          <span>Portfolio</span>
          <small>Portfolio to simulate</small>
          <span className="simulation-select">
            <Icon name="wallet" size={18} />
            <select value={portfolio.id} onChange={event => go(`simulations/${event.target.value}`)}>
              <option value={portfolio.id}>{portfolio.name}</option>
            </select>
            <Icon name="chevron-down" size={16} />
          </span>
        </label>
        <HistoricalScenarioSelector scenarioId={scenarioId} onChange={onScenarioChange} />
        <button className="primary-btn run-simulation-btn" onClick={onRun}>
          <span>▶</span> Run Simulation
        </button>
      </div>
    </Card>
  );
}
