import React, { useEffect, useRef, useState } from 'react';
import { ScrollView, StyleSheet, Text } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { PortfolioSelector } from '../../components/simulations/PortfolioSelector';
import { ScenarioSelector } from '../../components/simulations/ScenarioSelector';
import { SimulationResults } from '../../components/simulations/SimulationResults';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { LoadingState } from '../../components/ui/LoadingState';
import { portfolioErrorMessage } from '../../portfolio/portfolioErrors';
import { simulationErrorMessage } from '../../simulation/simulationErrors';
import type { SimulationRunResult } from '../../simulation/SimulationProvider';
import { useSimulationPortfolio } from '../../simulation/useSimulationPortfolio';
import { useSimulations } from '../../simulation/useSimulations';
import { colors, spacing, typography } from '../../theme/theme';

export function HistoricalScenarioScreen({ route }: { route: any }) {
  const portfolioState = useSimulationPortfolio(route.params?.portfolioId);
  const { scenarios, scenarioStatus, scenarioError, refreshScenarios, runHistorical } = useSimulations();
  const [scenarioId, setScenarioId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [result, setResult] = useState<SimulationRunResult | null>(null);
  const runningRef = useRef(false);

  useEffect(() => {
    if (!scenarios.length) {
      setScenarioId(null);
    } else if (!scenarioId || !scenarios.some((scenario) => scenario.id === scenarioId)) {
      setScenarioId(scenarios[0].id);
    }
  }, [scenarioId, scenarios]);

  async function run() {
    if (runningRef.current || !portfolioState.portfolio || !scenarioId) return;
    runningRef.current = true;
    setRunning(true);
    setRunError(null);
    try {
      const response = await runHistorical(portfolioState.portfolio.id, scenarioId);
      setResult({ type: 'historical-scenario', response });
    } catch (error) {
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
    return <SafeAreaView style={styles.safe}><Card style={styles.errorCard}>
      <Text style={styles.error}>{portfolioErrorMessage(portfolioState.listError)}</Text>
      <Button title="Retry portfolios" onPress={() => void portfolioState.refreshPortfolios()} />
    </Card></SafeAreaView>;
  }
  const portfolioFailure = portfolioState.listStatus === 'error'
    ? portfolioErrorMessage(portfolioState.listError)
    : portfolioState.detailStatus === 'error'
      ? portfolioErrorMessage(portfolioState.detailError)
      : null;

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Historical Scenario</Text>
        <Text style={styles.subtitle}>Run a backend-defined historical event against a saved portfolio.</Text>

        {!portfolioState.portfolios.length ? (
          <Card><EmptyState title="No portfolio available" description="Create a portfolio with holdings before running a simulation." /></Card>
        ) : (
          <>
            <Text style={styles.section}>Portfolio</Text>
            <PortfolioSelector
              disabled={running}
              portfolios={portfolioState.portfolios}
              selectedId={portfolioState.selectedPortfolioId}
              onSelect={(id) => {
                if (runningRef.current) return;
                setResult(null);
                portfolioState.choosePortfolio(id);
              }}
            />
            {portfolioState.detailStatus === 'loading' ? <Text style={styles.state}>Loading holdings…</Text> : null}
            {portfolioFailure ? (
              <Card style={styles.errorCard}>
                <Text style={styles.error}>{portfolioFailure}</Text>
                <Button title="Retry portfolio" onPress={() => void (portfolioState.listStatus === 'error' ? portfolioState.refreshPortfolios() : portfolioState.retryPortfolio())} />
              </Card>
            ) : null}

            <Text style={styles.section}>Scenario</Text>
            {scenarioStatus === 'loading' && !scenarios.length ? <Text style={styles.state}>Loading backend scenarios…</Text> : null}
            {scenarioStatus === 'error' ? (
              <Card style={styles.errorCard}>
                <Text style={styles.error}>{simulationErrorMessage(scenarioError, 'Unable to load historical scenarios.')}</Text>
                <Button title="Retry scenarios" onPress={() => void refreshScenarios()} />
              </Card>
            ) : scenarios.length ? (
              <ScenarioSelector disabled={running} scenarios={scenarios} selectedId={scenarioId} onSelect={(id) => { if (runningRef.current) return; setScenarioId(id); setResult(null); }} />
            ) : scenarioStatus === 'ready' ? (
              <Card><EmptyState title="No scenarios available" description="The backend did not return any historical scenarios." /></Card>
            ) : null}

            {runError ? <Card style={styles.errorCard}><Text style={styles.error}>{runError}</Text></Card> : null}
            {portfolioState.portfolio && !portfolioState.portfolio.holdings.length ? <Text style={styles.state}>Add saved holdings before running a simulation.</Text> : null}
            <Button
              title={running ? 'Running…' : 'Run historical scenario'}
              onPress={() => void run()}
              disabled={running || !portfolioState.portfolio?.holdings.length || !scenarioId || scenarioStatus !== 'ready'}
              style={{ marginTop: spacing.xl }}
            />
            {result ? <SimulationResults result={result} /> : null}
          </>
        )}
      </ScrollView>
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
  errorCard: { gap: spacing.md, borderColor: colors.dangerBorder, marginBottom: spacing.md },
  error: { color: colors.danger, lineHeight: 18, fontSize: 12 }
});
