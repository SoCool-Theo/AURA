import { useEffect, useMemo, useState } from 'react';
import {
  getPlannedPortfolioAllocation,
  getPortfolio,
  getPortfolioValuation,
  listPortfolios,
} from '../../api/portfoliosApi';
import { getPortfolioReport, listPortfolioReports } from '../../api/reportsApi';
import { listHistoricalScenarios, runAllocationSimulation, runCombinedSimulation, runHistoricalScenario } from '../../api/simulationsApi';
import { go } from '../../app/routes';
import { InlineErrorCard, ScreenErrorState } from '../../components/ui/ApiErrorState';
import { Card } from '../../components/ui/Card';
import type { PortfolioHoldingInput, PortfolioResponse, PortfolioSummaryResponse } from '../../types/portfolio';
import type { PortfolioReportResponse } from '../../types/report';
import type { HistoricalScenarioResponse, SimulationAllocation, SimulationMode, SimulationRunResult } from '../../types/simulation';
import styles from './SimulationIntegration.module.css';
import { AllocationEditor } from './components/AllocationEditor';
import { SimulationHistory } from './components/SimulationHistory';
import { SimulationModeSelector } from './components/SimulationModeSelector';
import { SimulationResults } from './components/SimulationResults';
import { SimulationSetup } from './components/SimulationSetup';
import {
  allocationInputsFromPlannedAllocation,
  allocationInputsFromPortfolio,
  allocationInputsFromValuation,
  rebalanceAllocationInputs,
  validateModifiedAllocation,
} from './simulationUi';

interface Props { portfolioId?: string }

function localIsoDate(date: Date): string { return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`; }
function defaultPeriod() { const end = new Date(); const start = new Date(end); start.setFullYear(start.getFullYear() - 1); return { start: localIsoDate(start), end: localIsoDate(end) }; }
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
  const [baselineAllocation, setBaselineAllocation] = useState<SimulationAllocation>({});
  const [originalAllocation, setOriginalAllocation] = useState<PortfolioHoldingInput[]>([]);
  const [result, setResult] = useState<SimulationRunResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [actionError, setActionError] = useState<unknown>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [historyReloadKey, setHistoryReloadKey] = useState(0);
  const [latestAnalysis, setLatestAnalysis] = useState<PortfolioReportResponse | null>(null);
  const [latestAnalysisStatus, setLatestAnalysisStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [latestAnalysisError, setLatestAnalysisError] = useState<unknown>(null);

  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setLoadError(null); setActionError(null); setPortfolio(null); setResult(null); setAllocation({}); setBaselineAllocation({}); setOriginalAllocation([]);
    Promise.all([listPortfolios({ signal: controller.signal }), listHistoricalScenarios(controller.signal)])
      .then(([portfolioResponse, scenarioResponse]) => {
        setPortfolios(portfolioResponse.portfolios); setScenarios(scenarioResponse.scenarios);
        const requestedExists = portfolioId ? portfolioResponse.portfolios.some(item => item.id === portfolioId) : false;
        if (portfolioId && !requestedExists) { setSelectedPortfolioId(''); setLoadError('Portfolio not found.'); return; }
        const selected = portfolioId || portfolioResponse.portfolios[0]?.id || '';
        setSelectedPortfolioId(selected); setScenarioId(current => scenarioResponse.scenarios.some(item => item.id === current) ? current : scenarioResponse.scenarios[0]?.id ?? '');
        if (selected) return getPortfolio(selected, { signal: controller.signal }).then(async detail => {
          let inputs: SimulationAllocation;
          let savedAllocation: PortfolioHoldingInput[];
          if (detail.portfolio_type === 'PLANNED' && detail.holdings.length) {
            const planned = await getPlannedPortfolioAllocation(detail.id, { signal: controller.signal });
            inputs = allocationInputsFromPlannedAllocation(planned);
            savedAllocation = planned.holdings.map(holding => ({
              symbol: holding.symbol,
              weight: Number(holding.target_allocation),
            }));
          } else if (detail.portfolio_type === 'CURRENT' && detail.holdings.length) {
            const valuation = await getPortfolioValuation(detail.id, 'USD', { signal: controller.signal });
            inputs = allocationInputsFromValuation(valuation);
            savedAllocation = valuation.holdings.map(holding => ({
              symbol: holding.symbol,
              weight: Number(holding.current_allocation),
            }));
          } else {
            inputs = allocationInputsFromPortfolio(detail);
            savedAllocation = detail.holdings.flatMap(holding => holding.weight === null
              ? []
              : [{ symbol: holding.symbol, weight: holding.weight }]);
          }
          setPortfolio(detail);
          setAllocation(inputs);
          setBaselineAllocation(inputs);
          setOriginalAllocation(savedAllocation);
        });
      })
      .catch(requestError => { if (!controller.signal.aborted) setLoadError(requestError); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [portfolioId, reloadKey]);

  useEffect(() => {
    const controller = new AbortController();
    setLatestAnalysis(null);
    setLatestAnalysisError(null);
    if (!selectedPortfolioId) {
      setLatestAnalysisStatus('idle');
      return () => controller.abort();
    }

    setLatestAnalysisStatus('loading');
    void listPortfolioReports(selectedPortfolioId, { signal: controller.signal })
      .then(async response => {
        const newest = response.reports[0];
        if (!newest) return null;
        return getPortfolioReport(selectedPortfolioId, newest.id, { signal: controller.signal });
      })
      .then(report => {
        if (controller.signal.aborted) return;
        setLatestAnalysis(report);
        setLatestAnalysisStatus('ready');
      })
      .catch(error => {
        if (controller.signal.aborted) return;
        setLatestAnalysisError(error);
        setLatestAnalysisStatus('error');
      });
    return () => controller.abort();
  }, [selectedPortfolioId]);

  const totalAllocation = Object.values(allocation).reduce((sum, value) => sum + Number(value), 0);
  function clearOutput() { setResult(null); setActionError(null); }
  function resetAllocation() { setAllocation(baselineAllocation); clearOutput(); }

  async function run() {
    if (running) return;
    if (!selectedPortfolioId || !portfolio) { setActionError('Choose a portfolio before running a simulation.'); return; }
    if (!portfolio.holdings.length) { setActionError('This portfolio has no saved holdings to simulate.'); return; }
    if (mode === 'allocation' && (!startDate || !endDate)) { setActionError('Choose both requested dates.'); return; }
    if (mode === 'allocation' && startDate > endDate) { setActionError('Start date must be on or before end date.'); return; }
    if (mode !== 'allocation' && !scenarioId) { setActionError('Choose a historical scenario.'); return; }
    const validatedAllocation = mode === 'historical-scenario'
      ? null
      : validateModifiedAllocation(portfolio, allocation);
    if (validatedAllocation?.error) { setActionError(validatedAllocation.error); return; }
    const modified_allocation = validatedAllocation?.allocation ?? [];
    setRunning(true); setActionError(null); setResult(null);
    try {
      const nextResult: SimulationRunResult = mode === 'historical-scenario'
        ? { type: mode, response: await runHistoricalScenario(selectedPortfolioId, { scenario_id: scenarioId }) }
        : mode === 'allocation'
          ? { type: mode, response: await runAllocationSimulation(selectedPortfolioId, { start_date: startDate, end_date: endDate, modified_allocation }) }
          : { type: mode, response: await runCombinedSimulation(selectedPortfolioId, { scenario_id: scenarioId, modified_allocation }) };
      setResult(nextResult); setHistoryReloadKey(value => value + 1);
    } catch (requestError) { setActionError(requestError); }
    finally { setRunning(false); }
  }

  return <div className="page simulations-page">
    <header className="simulations-header"><div><h1>Simulations</h1><p>Explore how a saved allocation behaved in historical periods and scenarios.</p></div>{selectedPortfolioId && <button className="secondary-btn" onClick={() => document.getElementById('simulation-history')?.scrollIntoView({ behavior: 'smooth' })}>Simulation History</button>}</header>
    <SimulationModeSelector mode={mode} disabled={running} onChange={next => { setMode(next); clearOutput(); }} />
    <SimulationSetup portfolios={portfolios} portfolioId={selectedPortfolioId} mode={mode} scenarios={scenarios} scenarioId={scenarioId} startDate={startDate} endDate={endDate} loading={loading} running={running} onScenarioChange={value => { setScenarioId(value); clearOutput(); }} onStartDateChange={value => { setStartDate(value); clearOutput(); }} onEndDateChange={value => { setEndDate(value); clearOutput(); }} onRun={() => void run()} />
    {portfolio && <div className={[styles.modeContext, portfolio.portfolio_type === 'PLANNED' ? styles.plannedContext : ''].join(' ')}>
      <strong>{portfolio.portfolio_type === 'PLANNED' ? 'Hypothetical planned allocation' : portfolio.portfolio_type === 'CURRENT' ? 'Current portfolio baseline' : 'Legacy saved allocation'}</strong>
      <span>{portfolio.portfolio_type === 'PLANNED' ? 'Results describe how the proposed allocation would have behaved historically. They are not a forecast or an investment recommendation.' : portfolio.portfolio_type === 'CURRENT' ? 'The original allocation is derived from the current value of the saved shares.' : 'The original allocation uses the portfolio’s saved compatibility weights.'}</span>
    </div>}
    {mode !== 'historical-scenario' && portfolio && <AllocationEditor mode={mode} portfolio={portfolio} allocation={allocation} totalAllocation={totalAllocation} disabled={running} onReset={resetAllocation} onChange={(symbol, value, selectedSymbols) => { setAllocation(current => rebalanceAllocationInputs(current, selectedSymbols, symbol, value)); clearOutput(); }} />}
    {Boolean(actionError) && <InlineErrorCard error={actionError} fallbackMessage="Unable to run this simulation." />}
    {loading && <Card className={styles.state}><h2>Loading simulation setup</h2><p role="status">Retrieving your portfolios and Aura’s historical scenario catalogue.</p></Card>}
    {!loading && !loadError && !portfolios.length && <Card className={styles.state}><h2>No portfolios to simulate</h2><p>Create a portfolio and save its complete allocation first.</p><button className="primary-btn" onClick={() => go('create')}>Create Portfolio</button></Card>}
    {!loading && Boolean(loadError) && !portfolio && <ScreenErrorState error={loadError} fallbackMessage="Unable to load simulation setup." resourceName="Portfolio" onRetry={() => setReloadKey(value => value + 1)} />}
    {running && <Card className={styles.state}><h2>Running simulation</h2><p role="status">Aura is calculating and saving one immutable simulation snapshot.</p></Card>}
    {result && !running && <><div className={styles.saved}><strong>Simulation saved.</strong> This successful run is already available in history.</div><SimulationResults result={result} originalAllocation={originalAllocation} latestAnalysis={latestAnalysis} latestAnalysisStatus={latestAnalysisStatus} latestAnalysisError={latestAnalysisError} onViewLatestAnalysis={latestAnalysis ? () => go(`reports/${latestAnalysis.portfolio_id}/${latestAnalysis.id}`) : undefined} /></>}
    {!loading && selectedPortfolioId && <SimulationHistory portfolioId={selectedPortfolioId} reloadKey={historyReloadKey} />}
  </div>;
}
