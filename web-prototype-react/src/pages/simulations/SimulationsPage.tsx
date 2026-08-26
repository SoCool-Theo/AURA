import { useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import type { Portfolio } from '../../types/portfolio';
import type { ReportSummary } from '../../types/report';
import type { SimulationAllocation, SimulationMode } from '../../types/simulation';
import { scenarioOptions } from '../../mocks/simulations.mock';
import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import { AllocationEditor } from './components/AllocationEditor';
import { SimulationHistory } from './components/SimulationHistory';
import { SimulationModeSelector } from './components/SimulationModeSelector';
import { SimulationResults } from './components/SimulationResults';
import { SimulationSetup } from './components/SimulationSetup';

interface SimulationsPageProps {
  portfolio: Portfolio;
  setReports: Dispatch<SetStateAction<ReportSummary[]>>;
}

export function SimulationsPage({ portfolio, setReports }: SimulationsPageProps) {
  const [mode, setMode] = useState<SimulationMode>('Historical Scenario');
  const [scenarioId, setScenarioId] = useState('gfc');
  const [ran, setRan] = useState(true);
  const [allocation, setAllocation] = useState<SimulationAllocation>(() => (
    Object.fromEntries(portfolio.holdings.map(holding => [holding.symbol, holding.weight]))
  ));
  const scenario = scenarioOptions.find(option => option.id === scenarioId);

  if (!scenario) return null;
  const currentScenario = scenario;

  const totalAllocation = Object.values(allocation).reduce(
    (sum, weight) => sum + Number(weight || 0),
    0,
  );
  const allocationEffect = (100 - totalAllocation) * .02
    + (Number(allocation.BND || 0) - 15) * .18
    - (Number(allocation.NVDA || 0) - 57) * .12;
  const simulatedReturn = scenario.returnPct
    + (mode === 'Historical Scenario' ? 0 : allocationEffect);

  function run() {
    if (mode !== 'Historical Scenario' && Math.abs(totalAllocation - 100) > .01) {
      return alert('Allocation must total 100%.');
    }
    setRan(true);
  }

  function save() {
    const report: ReportSummary = {
      id: Date.now(),
      name: `${currentScenario.label} ${mode}`,
      portfolio: portfolio.name,
      type: 'Simulation',
      date: new Date().toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      }),
      riskScore: null,
    };
    setReports(previous => [report, ...previous]);
    alert('Simulation saved to Reports.');
  }

  function resetAllocation() {
    setAllocation(Object.fromEntries(
      portfolio.holdings.map(holding => [holding.symbol, holding.weight]),
    ));
    setRan(false);
  }

  function changeMode(nextMode: SimulationMode) {
    setMode(nextMode);
    setRan(false);
  }

  function changeScenario(nextScenarioId: string) {
    setScenarioId(nextScenarioId);
    setRan(false);
  }

  function changeAllocation(symbol: string, weight: number) {
    setAllocation(previous => ({ ...previous, [symbol]: weight }));
    setRan(false);
  }

  return (
    <div className="page simulations-page">
      <header className="simulations-header">
        <div>
          <h1>Simulations</h1>
          <p>Explore how your portfolio might have behaved during historical market conditions.</p>
        </div>
        <SimulationHistory />
      </header>

      <SimulationModeSelector mode={mode} onChange={changeMode} />
      <SimulationSetup
        portfolio={portfolio}
        scenarioId={scenarioId}
        onScenarioChange={changeScenario}
        onRun={run}
      />

      {mode !== 'Historical Scenario' && (
        <AllocationEditor
          mode={mode}
          portfolio={portfolio}
          allocation={allocation}
          totalAllocation={totalAllocation}
          onReset={resetAllocation}
          onChange={changeAllocation}
        />
      )}

      {!ran && (
        <Card className="simulation-ready-state">
          <span><Icon name="simulations" size={27} /></span>
          <div>
            <h2>Ready to run {mode.toLowerCase()}</h2>
            <p>Review the setup above, then run the simulation to generate historical results.</p>
          </div>
          <button className="primary-btn" onClick={run}>Run Simulation <span>→</span></button>
        </Card>
      )}

      {ran && (
        <SimulationResults
          portfolio={portfolio}
          scenario={scenario}
          mode={mode}
          simulatedReturn={simulatedReturn}
          allocationEffect={allocationEffect}
          onSave={save}
        />
      )}
    </div>
  );
}
