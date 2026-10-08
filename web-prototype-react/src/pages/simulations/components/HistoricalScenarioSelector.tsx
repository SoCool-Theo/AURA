import type { HistoricalScenarioResponse } from '../../../types/simulation';
import { AuraSelect } from '../../../components/ui/AuraSelect';
import type { AuraSelectOption } from '../../../components/ui/AuraSelect';

interface Props { scenarios: HistoricalScenarioResponse[]; scenarioId: string; loading?: boolean; disabled?: boolean; onChange: (id: string) => void }

export function HistoricalScenarioSelector({ scenarios, scenarioId, loading, disabled, onChange }: Props) {
  const options: AuraSelectOption<string>[] = scenarios.map(item => ({ value: item.id, label: item.display_name, description: `${item.requested_start_date} to ${item.requested_end_date}`, icon: 'calendar', tone: 'amber' }));
  return <div className="simulation-control-field"><span>Historical scenario</span><small>Choose a saved historical period to explore</small>
    {loading
      ? <div className="simulation-select" role="status">Loading scenarios…</div>
      : <AuraSelect className="simulation-select simulation-aura-select" ariaLabel="Historical scenario" value={scenarioId} options={options} onChange={onChange} disabled={disabled} />}
  </div>;
}
