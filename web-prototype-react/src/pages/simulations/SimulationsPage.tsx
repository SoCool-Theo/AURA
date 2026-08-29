import { useEffect, useMemo, useState } from 'react';
import { getPortfolio, listPortfolios } from '../../api/portfoliosApi';
import { listHistoricalScenarios, runAllocationSimulation, runCombinedSimulation, runHistoricalScenario } from '../../api/simulationsApi';
import { go } from '../../app/routes';
import { Card } from '../../components/ui/Card';
import type { PortfolioResponse, PortfolioSummaryResponse } from '../../types/portfolio';
import type { HistoricalScenarioResponse, SimulationAllocation, SimulationMode, SimulationRunResult } from '../../types/simulation';
import styles from './SimulationIntegration.module.css';
import { AllocationEditor } from './components/AllocationEditor';
import { SimulationHistory } from './components/SimulationHistory';
import { SimulationModeSelector } from './components/SimulationModeSelector';
import { SimulationResults } from './components/SimulationResults';
import { SimulationSetup } from './components/SimulationSetup';
import { simulationErrorMessage } from './simulationUi';

interface Props { portfolioId?: string }

function localIsoDate(date: Date): string { return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`; }
function defaultPeriod() { const end = new Date(); const start = new Date(end); start.setFullYear(start.getFullYear() - 1); return { start: localIsoDate(start), end: localIsoDate(end) }; }
function allocationFromPortfolio(portfolio: PortfolioResponse): SimulationAllocation { return Object.fromEntries(portfolio.holdings.map(item => [item.symbol, String(item.weight * 100)])); }

export function SimulationsPage({ portfolioId }: Props) {
  const period = useMemo(defaultPeriod, []);
  const [portfolios, setPortfolios] = useState<PortfolioSummaryResponse[]>([]);
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);
  const [scenarios, setScenarios] = useState<HistoricalScenarioResponse[]>([]);
  const [selectedPortfolioId, setSelectedPortfolioId] = useState('');
  const [mode, setMode] = useState<SimulationMode>('historical-scenario');
  const [scenarioId, setScenarioId] = useState('');
  const [startDate, setStartDate] = useState(period.start);
  const [endDate, setEndDate] = useState(period.end);
  const [allocation, setAllocation] = useState<SimulationAllocation>({});
  const [result, setResult] = useState<SimulationRunResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [historyReloadKey, setHistoryReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError(null); setPortfolio(null); setResult(null);
    Promise.all([listPortfolios({ signal: controller.signal }), listHistoricalScenarios(controller.signal)])
      .then(([portfolioResponse, scenarioResponse]) => {
        setPortfolios(portfolioResponse.portfolios); setScenarios(scenarioResponse.scenarios);
        const requestedExists = portfolioId ? portfolioResponse.portfolios.some(item => item.id === portfolioId) : false;
        if (portfolioId && !requestedExists) { setSelectedPortfolioId(''); setError('Portfolio not found'); return; }
        const selected = portfolioId || portfolioResponse.portfolios[0]?.id || '';
        setSelectedPortfolioId(selected); setScenarioId(current => scenarioResponse.scenarios.some(item => item.id === current) ? current : scenarioResponse.scenarios[0]?.id ?? '');
        if (selected) return getPortfolio(selected, { signal: controller.signal }).then(detail => { setPortfolio(detail); setAllocation(allocationFromPortfolio(detail)); });
      })
      .catch(requestError => { if (!controller.signal.aborted) setError(simulationErrorMessage(requestError, 'Unable to load simulation setup.')); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [portfolioId, reloadKey]);

  const totalAllocation = Object.values(allocation).reduce((sum, value) => sum + Number(value), 0);
  function clearOutput() { setResult(null); setError(null); }
  function resetAllocation() { if (portfolio) setAllocation(allocationFromPortfolio(portfolio)); clearOutput(); }

  async function run() {
    if (!selectedPortfolioId || !portfolio) { setError('Choose a portfolio before running a simulation.'); return; }
    if (!portfolio.holdings.length) { setError('This portfolio has no saved holdings to simulate.'); return; }
    if (mode === 'allocation' && (!startDate || !endDate)) { setError('Choose both requested dates.'); return; }
    if (mode !== 'allocation' && !scenarioId) { setError('Choose a historical scenario.'); return; }
    const modified_allocation = portfolio.holdings.map(holding => ({ symbol: holding.symbol, weight: Number(allocation[holding.symbol]) / 100 }));
    if (mode !== 'historical-scenario' && modified_allocation.some(item => !Number.isFinite(item.weight))) { setError('Every saved symbol needs a numeric weight.'); return; }
    setRunning(true); setError(null); setResult(null);
    try {
      const nextResult: SimulationRunResult = mode === 'historical-scenario'
        ? { type: mode, response: await runHistoricalScenario(selectedPortfolioId, { scenario_id: scenarioId }) }
        : mode === 'allocation'
          ? { type: mode, response: await runAllocationSimulation(selectedPortfolioId, { start_date: startDate, end_date: endDate, modified_allocation }) }
          : { type: mode, response: await runCombinedSimulation(selectedPortfolioId, { scenario_id: scenarioId, modified_allocation }) };
      setResult(nextResult); setHistoryReloadKey(value => value + 1);
    } catch (requestError) { setError(simulationErrorMessage(requestError, 'Unable to run this simulation.')); }
    finally { setRunning(false); }
  }

  return <div className="page simulations-page">
    <header className="simulations-header"><div><h1>Simulations</h1><p>Run Aura’s real historical, allocation, and combined backend workflows.</p></div>{selectedPortfolioId && <button className="secondary-btn" onClick={() => document.getElementById('simulation-history')?.scrollIntoView({ behavior: 'smooth' })}>Simulation History</button>}</header>
    <SimulationModeSelector mode={mode} onChange={next => { setMode(next); clearOutput(); }} />
    <SimulationSetup portfolios={portfolios} portfolioId={selectedPortfolioId} mode={mode} scenarios={scenarios} scenarioId={scenarioId} startDate={startDate} endDate={endDate} loading={loading} running={running} onScenarioChange={value => { setScenarioId(value); clearOutput(); }} onStartDateChange={value => { setStartDate(value); clearOutput(); }} onEndDateChange={value => { setEndDate(value); clearOutput(); }} onRun={() => void run()} />
    {mode !== 'historical-scenario' && portfolio && <AllocationEditor mode={mode} portfolio={portfolio} allocation={allocation} totalAllocation={totalAllocation} disabled={running} onReset={resetAllocation} onChange={(symbol, value) => { setAllocation(current => ({ ...current, [symbol]: value })); clearOutput(); }} />}
    {error && <p className={styles.error} role="alert">{error}</p>}
    {loading && <Card className={styles.state}><h2>Loading simulation setup</h2><p role="status">Retrieving your portfolios and Aura’s historical scenario catalogue.</p></Card>}
    {!loading && !error && !portfolios.length && <Card className={styles.state}><h2>No portfolios to simulate</h2><p>Create a portfolio and save its complete allocation first.</p><button className="primary-btn" onClick={() => go('create')}>Create Portfolio</button></Card>}
    {!loading && error && !portfolio && <Card className={styles.state}><h2>Simulation setup unavailable</h2><p>The requested portfolio is unavailable or setup could not be loaded.</p><button className="primary-btn" onClick={() => setReloadKey(value => value + 1)}>Try Again</button></Card>}
    {running && <Card className={styles.state}><h2>Running simulation</h2><p role="status">Aura is calculating and saving one immutable simulation snapshot.</p></Card>}
    {result && !running && <><div className={styles.saved}><strong>Simulation saved.</strong> A successful backend run is already present in history; no separate save action is needed.</div><SimulationResults result={result} /></>}
    {!loading && selectedPortfolioId && <SimulationHistory portfolioId={selectedPortfolioId} reloadKey={historyReloadKey} />}
  </div>;
}
