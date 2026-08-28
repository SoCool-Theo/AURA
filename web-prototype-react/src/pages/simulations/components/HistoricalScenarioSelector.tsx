import { scenarioOptions } from '../../../mocks/simulations.mock';
import { AuraSelect } from '../../../components/ui/AuraSelect';
import type { AuraSelectOption } from '../../../components/ui/AuraSelect';

interface HistoricalScenarioSelectorProps {
  scenarioId: string;
  onChange: (scenarioId: string) => void;
}

export function HistoricalScenarioSelector({
  scenarioId,
  onChange,
}: HistoricalScenarioSelectorProps) {
  const options: AuraSelectOption<string>[] = scenarioOptions.map(option => ({
    value: option.id,
    label: option.label,
    description: option.dates,
    icon: 'calendar',
    tone: option.returnPct < 0 ? 'red' : 'green',
  }));

  return (
    <div className="simulation-control-field">
      <span>Historical scenario</span>
      <small>Market period to replay</small>
      <AuraSelect className="simulation-select simulation-aura-select" ariaLabel="Historical scenario" value={scenarioId} options={options} onChange={onChange} />
    </div>
  );
}
