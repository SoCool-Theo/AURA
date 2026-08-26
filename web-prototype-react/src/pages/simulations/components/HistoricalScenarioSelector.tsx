import { scenarioOptions } from '../../../mocks/simulations.mock';
import { Icon } from '../../../components/ui/Icon';

interface HistoricalScenarioSelectorProps {
  scenarioId: string;
  onChange: (scenarioId: string) => void;
}

export function HistoricalScenarioSelector({
  scenarioId,
  onChange,
}: HistoricalScenarioSelectorProps) {
  return (
    <label>
      <span>Historical scenario</span>
      <small>Market period to replay</small>
      <span className="simulation-select">
        <Icon name="calendar" size={18} />
        <select value={scenarioId} onChange={event => onChange(event.target.value)}>
          {scenarioOptions.map(option => (
            <option value={option.id} key={option.id}>{option.label} — {option.dates}</option>
          ))}
        </select>
        <Icon name="chevron-down" size={16} />
      </span>
    </label>
  );
}
