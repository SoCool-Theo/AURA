import type { SimulationMode } from '../../../types/simulation';
import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';

interface SimulationModeSelectorProps { mode: SimulationMode; disabled?: boolean; onChange: (mode: SimulationMode) => void }

const MODES: Array<[SimulationMode, string, string, string, string]> = [
  ['historical-scenario', 'Historical Scenario', 'time', 'purple', 'Replay the saved allocation through a historical scenario'],
  ['allocation', 'Allocation Change', 'pie-chart', 'cyan', 'Compare saved and modified allocations over exact dates'],
  ['combined', 'Combined Simulation', 'compare', 'blue', 'Compare allocations inside a historical scenario'],
];

export function SimulationModeSelector({ mode, disabled, onChange }: SimulationModeSelectorProps) {
  return <Card className="simulation-mode-card">
    <div className="simulation-mode-heading"><h2>Choose a simulation type</h2><p>Each successful run is saved as an immutable historical snapshot.</p></div>
    <div className="simulation-mode-options">{MODES.map(([value, label, icon, tone, description]) => <button key={value} aria-pressed={mode === value} className={mode === value ? 'active' : ''} onClick={() => onChange(value)} disabled={disabled}>
      <span className={`simulation-mode-icon ${tone}`}><Icon name={icon} size={20} /></span><span><strong>{label}</strong><small>{description}</small></span><i>{mode === value ? '✓' : ''}</i>
    </button>)}</div>
  </Card>;
}
