import type { SimulationMode } from '../../../types/simulation';
import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';

interface SimulationModeSelectorProps { mode: SimulationMode; disabled?: boolean; onChange: (mode: SimulationMode) => void }

const MODES: Array<[SimulationMode, string, string, string]> = [
  ['historical-scenario', 'Historical Scenario', 'reports', 'Replay the saved allocation through a backend scenario'],
  ['allocation', 'Allocation Change', 'trend', 'Compare saved and modified allocations over exact dates'],
  ['combined', 'Combined Simulation', 'simulations', 'Compare allocations inside a backend historical scenario'],
];

export function SimulationModeSelector({ mode, disabled, onChange }: SimulationModeSelectorProps) {
  return <Card className="simulation-mode-card">
    <div className="simulation-mode-heading"><h2>Choose a simulation type</h2><p>Each run uses one of Aura’s persisted backend simulation workflows.</p></div>
    <div className="simulation-mode-options">{MODES.map(([value, label, icon, description]) => <button key={value} aria-pressed={mode === value} className={mode === value ? 'active' : ''} onClick={() => onChange(value)} disabled={disabled}>
      <span className="simulation-mode-icon"><Icon name={icon} size={20} /></span><span><strong>{label}</strong><small>{description}</small></span><i>{mode === value ? '✓' : ''}</i>
    </button>)}</div>
  </Card>;
}
