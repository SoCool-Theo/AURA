import type { ScenarioOption } from '../../../types/simulation';
import { pct } from '../../../utils/formatting';
import { Card } from '../../../components/ui/Card';

interface SimulationComparisonProps {
  scenario: ScenarioOption;
  simulatedReturn: number;
}

export function SimulationComparison({
  scenario,
  simulatedReturn,
}: SimulationComparisonProps) {
  const difference = simulatedReturn - scenario.returnPct;

  return (
    <Card className="simulation-comparison-card">
      <div className="simulation-card-heading">
        <div>
          <h2>Original vs Modified Allocation</h2>
          <p>How the allocation adjustment changed the historical result.</p>
        </div>
      </div>
      <div className="simulation-comparison-grid">
        <div><small>Original allocation</small><strong>{pct(scenario.returnPct)}</strong><span>Historical return</span></div>
        <span className="comparison-arrow">→</span>
        <div className="highlight">
          <small>Modified allocation</small>
          <strong className={simulatedReturn > scenario.returnPct ? 'green-text' : 'red-text'}>{pct(simulatedReturn)}</strong>
          <span>Historical return</span>
        </div>
        <div>
          <small>Difference</small>
          <strong className={difference >= 0 ? 'green-text' : 'red-text'}>{pct(difference)}</strong>
          <span>Allocation effect</span>
        </div>
      </div>
    </Card>
  );
}
