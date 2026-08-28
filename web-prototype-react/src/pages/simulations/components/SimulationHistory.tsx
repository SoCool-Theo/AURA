import { go } from '../../../app/routes';
import { Icon } from '../../../components/ui/Icon';

export function SimulationHistory() {
  return (
    <button className="secondary-btn" onClick={() => go('reports')}>
      <Icon name="reports" size={17} /> Simulation History
    </button>
  );
}
