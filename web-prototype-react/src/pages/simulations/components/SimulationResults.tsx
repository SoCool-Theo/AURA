import type { Portfolio } from '../../../types/portfolio';
import type { ScenarioOption, SimulationMode } from '../../../types/simulation';
import { downturnA, downturnB, lineA, lineB } from '../../../mocks/dashboard.mock';
import { go } from '../../../app/routes';
import { LineChart } from '../../../components/charts/LineChart';
import { PortfolioMetric } from '../../../components/portfolio/PortfolioMetric';
import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';
import { pct } from '../../../utils/formatting';
import { SimulationComparison } from './SimulationComparison';

interface SimulationResultsProps {
  portfolio: Portfolio;
  scenario: ScenarioOption;
  mode: SimulationMode;
  simulatedReturn: number;
  allocationEffect: number;
  onSave: () => void;
}

export function SimulationResults({
  portfolio,
  scenario,
  mode,
  simulatedReturn,
  allocationEffect,
  onSave,
}: SimulationResultsProps) {
  const isNegativeScenario = scenario.returnPct < 0;

  return (
    <section className="simulation-results">
      <div className="simulation-results-heading">
        <div><span>SIMULATION RESULTS</span><h2>{scenario.label}</h2><p>{mode} · {portfolio.name}</p></div>
        <span className="results-status"><i /> Completed</span>
      </div>
      <div className="simulation-metric-grid">
        <PortfolioMetric label="Total Return" value={pct(simulatedReturn)} detail={scenario.label} icon="trend" tone={simulatedReturn < 0 ? 'red' : 'green'} />
        <PortfolioMetric label="Maximum Drawdown" value={`${(scenario.drawdown + allocationEffect * .7).toFixed(2)}%`} detail="Peak-to-trough decline" icon="drawdown" tone="red" />
        <PortfolioMetric label="Annualized Volatility" value={`${Math.max(8, scenario.volatility - allocationEffect * .25).toFixed(2)}%`} detail="Historical variation" icon="trend" tone="purple" />
        <PortfolioMetric label="Recovery Time" value={`${Math.max(1, Math.round(scenario.recovery - allocationEffect * .1))} months`} detail="Estimated historical recovery" icon="calendar" tone="blue" />
      </div>
      <div className="simulation-results-grid">
        <Card className="simulation-chart-card">
          <div className="simulation-card-heading">
            <div><h2>Portfolio Value Over Time</h2><p>Historical portfolio and benchmark paths</p></div>
            <div className="detail-chart-legend"><span className="p-dot" />Your Portfolio <span className="b-dot" />Benchmark</div>
          </div>
          <LineChart
            primary={isNegativeScenario ? downturnA : lineA}
            secondary={isNegativeScenario ? downturnB : lineB}
            negative={isNegativeScenario}
            height={285}
            area
          />
        </Card>
        <Card className="simulation-scenario-card">
          <div className="simulation-card-heading"><div><h2>Scenario Details</h2><p>Inputs used for this result</p></div></div>
          <div className="scenario-summary-icon"><Icon name="reports" size={22} /></div>
          <p>This simulation applies historical market movements from <strong>{scenario.label}</strong> to the selected portfolio.</p>
          <dl>
            <div><dt>Event period</dt><dd>{scenario.dates}</dd></div>
            <div><dt>Simulation mode</dt><dd>{mode}</dd></div>
            <div><dt>Data basis</dt><dd>Historical prices</dd></div>
          </dl>
          <div className="scenario-actions">
            <button className="secondary-btn" onClick={onSave}>Save Result</button>
            <button className="primary-btn" onClick={() => go('assistant')}>Ask Aura <span>→</span></button>
          </div>
        </Card>
      </div>
      {mode === 'Combined Simulation' && (
        <SimulationComparison scenario={scenario} simulatedReturn={simulatedReturn} />
      )}
    </section>
  );
}
