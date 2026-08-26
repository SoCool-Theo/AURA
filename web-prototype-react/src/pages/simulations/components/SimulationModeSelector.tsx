import type { SimulationMode } from '../../../types/simulation';
import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';

interface SimulationModeSelectorProps {
  mode: SimulationMode;
  onChange: (mode: SimulationMode) => void;
}

const SIMULATION_MODES: Array<[SimulationMode, string, string]> = [
  ['Historical Scenario', 'reports', 'Replay a historical market event'],
  ['Allocation Change', 'trend', 'Test a different asset allocation'],
  ['Combined Simulation', 'simulations', 'Change allocation within a scenario'],
];

export function SimulationModeSelector({ mode, onChange }: SimulationModeSelectorProps) {
  return (
    <Card className="simulation-mode-card">
      <div className="simulation-mode-heading">
        <h2>Choose a simulation type</h2>
        <p>Select what you want to test before configuring the scenario.</p>
      </div>
      <div className="simulation-mode-options">
        {SIMULATION_MODES.map(([label, icon, description]) => (
          <button
            key={label}
            aria-pressed={mode === label}
            className={mode === label ? 'active' : ''}
            onClick={() => onChange(label)}
          >
            <span className="simulation-mode-icon"><Icon name={icon} size={20} /></span>
            <span><strong>{label}</strong><small>{description}</small></span>
            <i>{mode === label ? '✓' : ''}</i>
          </button>
        ))}
      </div>
    </Card>
  );
}
