import type { Portfolio } from '../../../types/portfolio';
import { go } from '../../../app/routes';
import { Card } from '../../../components/ui/Card';
import { AuraSelect } from '../../../components/ui/AuraSelect';
import type { AuraSelectOption, AuraSelectTone } from '../../../components/ui/AuraSelect';
import { money } from '../../../utils/formatting';
import { HistoricalScenarioSelector } from './HistoricalScenarioSelector';

interface SimulationSetupProps {
  portfolio: Portfolio;
  portfolios: Portfolio[];
  scenarioId: string;
  onScenarioChange: (scenarioId: string) => void;
  onRun: () => void;
}

export function SimulationSetup({
  portfolio,
  portfolios,
  scenarioId,
  onScenarioChange,
  onRun,
}: SimulationSetupProps) {
  const portfolioOptions: AuraSelectOption<string>[] = portfolios.map(item => {
    const risk = item.riskLevel.toLowerCase();
    const tone: AuraSelectTone = risk.includes('high') ? 'red' : risk.includes('low') ? 'green' : 'amber';
    return {
      value: item.id,
      label: item.name,
      description: `${money(item.value)} · ${item.riskLevel}`,
      icon: 'wallet',
      tone,
    };
  });

  return (
    <Card className="simulation-setup-card">
      <div className="simulation-setup-heading">
        <div><span>SIMULATION SETUP</span><h2>Configure your test</h2></div>
        <small>Historical results are educational, not predictive.</small>
      </div>
      <div className="simulation-controls-grid">
        <div className="simulation-control-field">
          <span>Portfolio</span>
          <small>Portfolio to simulate</small>
          <AuraSelect className="simulation-select simulation-aura-select" ariaLabel="Portfolio to simulate" value={portfolio.id} options={portfolioOptions} onChange={portfolioId => go(`simulations/${portfolioId}`)} />
        </div>
        <HistoricalScenarioSelector scenarioId={scenarioId} onChange={onScenarioChange} />
        <button className="primary-btn run-simulation-btn" onClick={onRun}>
          <span>▶</span> Run Simulation
        </button>
      </div>
    </Card>
  );
}
