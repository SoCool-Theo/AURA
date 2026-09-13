import React, { useEffect, useRef, useState } from 'react';
import { StyleSheet, Text } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { AllocationEditor } from '../../components/simulations/AllocationEditor';
import { PortfolioSelector } from '../../components/simulations/PortfolioSelector';
import { ScenarioSelector } from '../../components/simulations/ScenarioSelector';
import { SimulationResults } from '../../components/simulations/SimulationResults';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { FormErrorSummary, InlineErrorCard, ScreenErrorState } from '../../components/ui/ErrorState';
import { LoadingState } from '../../components/ui/LoadingState';
import { KeyboardAwareScrollView } from '../../components/ui/KeyboardAwareScrollView';
import {
  portfolioErrorMessage,
  portfolioValuationErrorMessage
} from '../../portfolio/portfolioErrors';
import { simulationErrorMessage } from '../../simulation/simulationErrors';
import type { SimulationRunResult } from '../../simulation/SimulationProvider';
import {
  allocationInputsFromPortfolio,
  allocationInputsFromPlannedAllocation,
  allocationInputsFromValuation,
  allocationTotal,
  validateModifiedAllocation,
  type AllocationInputs
} from '../../simulation/simulationValidation';
import { useSimulationPortfolio } from '../../simulation/useSimulationPortfolio';
import { useSimulations } from '../../simulation/useSimulations';
import { colors, spacing, typography } from '../../theme/theme';
import { portfolioHoldingMode } from '../../types/portfolio';

export function CombinedSimulationScreen({ route }: { route: any }) {
  const portfolioState = useSimulationPortfolio(route.params?.portfolioId);
  const { scenarios, scenarioStatus, scenarioError, refreshScenarios, runCombined } = useSimulations();
  const [scenarioId, setScenarioId] = useState<string | null>(null);
  const [weights, setWeights] = useState<AllocationInputs>({});
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [runFailure, setRunFailure] = useState<unknown>(null);
  const [result, setResult] = useState<SimulationRunResult | null>(null);
  const runningRef = useRef(false);

  useEffect(() => {
    if (!scenarios.length) {
      setScenarioId(null);
    } else if (!scenarioId || !scenarios.some((scenario) => scenario.id === scenarioId)) {
      setScenarioId(scenarios[0].id);
    }
  }, [scenarioId, scenarios]);

  useEffect(() => {
    if (portfolioState.portfolio) {
      const mode = portfolioHoldingMode(portfolioState.portfolio.holdings);
      setWeights(mode === 'planned'
        ? portfolioState.plannedAllocation
          ? allocationInputsFromPlannedAllocation(portfolioState.plannedAllocation)
          : {}
        : mode === 'real'
          ? portfolioState.valuation
            ? allocationInputsFromValuation(portfolioState.valuation)
            : {}
          : allocationInputsFromPortfolio(portfolioState.portfolio));
      setResult(null);
      setRunError(null);
      setRunFailure(null);
    }
  }, [portfolioState.plannedAllocation, portfolioState.portfolio, portfolioState.valuation]);

  async function run() {
    const portfolio = portfolioState.portfolio;
    if (runningRef.current || !portfolio || !scenarioId) return;
    const validated = validateModifiedAllocation(portfolio, weights);
    if (!validated.allocation) {
      setRunFailure(null);
      setRunError(validated.error);
      return;
    }
    runningRef.current = true;
    setRunning(true);
    setRunError(null);
    setRunFailure(null);
    try {
      const response = await runCombined(portfolio.id, {
        scenario_id: scenarioId,
        modified_allocation: validated.allocation
      });
      setResult({ type: 'combined', response });
    } catch (error) {
      setRunFailure(error);
      setRunError(simulationErrorMessage(error));
    } finally {
      runningRef.current = false;
      setRunning(false);
    }
  }

  if ((portfolioState.listStatus === 'idle' || portfolioState.listStatus === 'loading') && !portfolioState.portfolios.length) {
    return <LoadingState message="Loading portfolios…" />;
  }
  if (portfolioState.listStatus === 'error' && !portfolioState.portfolios.length) {
    return <SafeAreaView style={styles.safe}><ScreenErrorState
      error={portfolioState.listError}
      resourceName="Portfolio list"
      fallbackMessage="Unable to load portfolios for simulation."
      onRetry={() => void portfolioState.refreshPortfolios()}
      retryTitle="Retry portfolios"
    /></SafeAreaView>;
  }
  const portfolioFailure = portfolioState.listStatus === 'error'
    ? portfolioState.listError
    : portfolioState.detailStatus === 'error'
      ? portfolioState.detailError
      : null;
  const holdingMode = portfolioState.portfolio
    ? portfolioHoldingMode(portfolioState.portfolio.holdings)
    : 'empty';
  const baselineReady = holdingMode === 'planned'
    ? Boolean(portfolioState.plannedAllocation)
    : holdingMode !== 'real' || Boolean(portfolioState.valuation);

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <KeyboardAwareScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Combined Simulation</Text>
        <Text style={styles.subtitle}>Compare original and modified allocations during one backend-defined scenario.</Text>

        {!portfolioState.portfolios.length ? (
          <Card><EmptyState title="No portfolio available" description="Create a portfolio with holdings before running a simulation." /></Card>
        ) : (
          <>
            <Text style={styles.section}>Portfolio</Text>
            <PortfolioSelector disabled={running} portfolios={portfolioState.portfolios} selectedId={portfolioState.selectedPortfolioId} onSelect={(id) => { if (!runningRef.current) portfolioState.choosePortfolio(id); }} />
            {portfolioState.detailStatus === 'loading' ? <Text style={styles.state}>Loading holdings…</Text> : null}
            {portfolioFailure ? <InlineErrorCard error={portfolioFailure} message={portfolioErrorMessage(portfolioFailure)} stale={Boolean(portfolioState.portfolio)} onRetry={() => void (portfolioState.listStatus === 'error' ? portfolioState.refreshPortfolios() : portfolioState.retryPortfolio())} retryTitle="Retry portfolio" /> : null}
            {portfolioState.valuationStatus === 'loading' ? <Text style={styles.state}>{holdingMode === 'planned' ? 'Loading target allocation from proposed amounts…' : 'Loading current USD allocation from backend valuation…'}</Text> : null}
            {portfolioState.valuationStatus === 'error' ? (
              <InlineErrorCard error={portfolioState.valuationError} message={holdingMode === 'planned' ? portfolioErrorMessage(portfolioState.valuationError, 'Unable to load the planned target allocation.') : portfolioValuationErrorMessage(portfolioState.valuationError)} onRetry={() => void portfolioState.retryPortfolio()} retryTitle={holdingMode === 'planned' ? 'Retry allocation' : 'Retry valuation'} />
            ) : null}

            <Text style={styles.section}>Scenario</Text>
            {scenarioStatus === 'loading' && !scenarios.length ? <Text style={styles.state}>Loading backend scenarios…</Text> : null}
            {scenarioStatus === 'error' ? (
              <InlineErrorCard error={scenarioError} message={simulationErrorMessage(scenarioError, 'Unable to load historical scenarios.')} stale={Boolean(scenarios.length)} onRetry={() => void refreshScenarios()} retryTitle="Retry scenarios" />
            ) : scenarios.length ? (
              <ScenarioSelector disabled={running} scenarios={scenarios} selectedId={scenarioId} onSelect={(id) => { if (runningRef.current) return; setScenarioId(id); setResult(null); }} />
            ) : scenarioStatus === 'ready' ? (
              <Card><EmptyState title="No scenarios available" description="The backend did not return any historical scenarios." /></Card>
            ) : null}

            {portfolioState.portfolio && !portfolioState.portfolio.holdings.length ? (
              <Card><EmptyState title="No holdings available" description="Add holdings to this portfolio before changing its allocation." /></Card>
            ) : portfolioState.portfolio && baselineReady ? (
              <>
                <Text style={styles.section}>Modified allocation</Text>
                <Text style={styles.state}>{holdingMode === 'real' ? 'Initialized from the backend-resolved current USD allocation.' : holdingMode === 'planned' ? 'Initialized from the backend-derived target allocation for this hypothetical plan.' : 'Initialized from the saved legacy allocation.'}</Text>
                <AllocationEditor disabled={running} portfolio={portfolioState.portfolio} inputs={weights} total={allocationTotal(weights)} onChange={(symbol, value) => setWeights((current) => ({ ...current, [symbol]: value }))} />
                {runError ? <FormErrorSummary error={runFailure} message={runError} /> : null}
                <Button title={running ? 'Running…' : 'Run combined simulation'} onPress={() => void run()} disabled={running || !scenarioId || scenarioStatus !== 'ready'} style={{ marginTop: spacing.xl }} />
                {result ? <SimulationResults result={result} /> : null}
              </>
            ) : null}
          </>
        )}
      </KeyboardAwareScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 100 },
  title: { color: colors.text, ...typography.h1 },
  subtitle: { color: colors.textSecondary, marginTop: 6, marginBottom: spacing.lg, lineHeight: 20 },
  section: { color: colors.text, fontSize: 14, fontWeight: '900', marginTop: spacing.lg, marginBottom: spacing.sm },
  state: { color: colors.textSecondary, marginBottom: spacing.lg },
  errorCard: { gap: spacing.md, borderColor: colors.dangerBorder, marginTop: spacing.md },
  error: { color: colors.danger, lineHeight: 18, fontSize: 12 }
});
