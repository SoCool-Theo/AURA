import React, { useEffect, useRef, useState } from 'react';
import { ScrollView, StyleSheet, Text } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { PortfolioSelector } from '../../components/simulations/PortfolioSelector';
import { ScenarioSelector } from '../../components/simulations/ScenarioSelector';
import { SimulationResults } from '../../components/simulations/SimulationResults';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { FormErrorSummary, InlineErrorCard, ScreenErrorState } from '../../components/ui/ErrorState';
import { LoadingState } from '../../components/ui/LoadingState';
import { portfolioErrorMessage, portfolioValuationErrorMessage } from '../../portfolio/portfolioErrors';
import { reportErrorMessage } from '../../report/reportErrors';
import { useReports } from '../../report/useReports';
import { simulationErrorMessage } from '../../simulation/simulationErrors';
import type { SimulationRunResult } from '../../simulation/SimulationProvider';
import { useSimulationPortfolio } from '../../simulation/useSimulationPortfolio';
import { useSimulations } from '../../simulation/useSimulations';
import { colors, spacing, typography } from '../../theme/theme';
import { portfolioHoldingMode, type PortfolioAllocationInput } from '../../types/portfolio';
import type { PortfolioReportResponse } from '../../types/report';

export function HistoricalScenarioScreen({ route, navigation }: { route: any; navigation: any }) {
  const portfolioState = useSimulationPortfolio(route.params?.portfolioId);
  const { scenarios, scenarioStatus, scenarioError, refreshScenarios, runHistorical } = useSimulations();
  const { getPortfolioReportHistory, getReport } = useReports();
  const [scenarioId, setScenarioId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [runFailure, setRunFailure] = useState<unknown>(null);
  const [result, setResult] = useState<SimulationRunResult | null>(null);
  const runningRef = useRef(false);
  const latestAnalysisRequestRef = useRef(0);
  const [latestAnalysis, setLatestAnalysis] = useState<PortfolioReportResponse | null>(null);
  const [latestAnalysisStatus, setLatestAnalysisStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [latestAnalysisError, setLatestAnalysisError] = useState<unknown>(null);

  const selectedPortfolioSummary = portfolioState.portfolios.find(
    (item) => item.id === portfolioState.selectedPortfolioId
  );

  const holdingMode = portfolioState.portfolio
    ? portfolioHoldingMode(portfolioState.portfolio.holdings)
    : 'empty';
  const baselineReady = holdingMode === 'planned'
    ? Boolean(portfolioState.plannedAllocation)
    : holdingMode !== 'real' || Boolean(portfolioState.valuation);
  const originalAllocation: PortfolioAllocationInput[] = holdingMode === 'planned'
    ? portfolioState.plannedAllocation?.holdings.map((holding) => ({
      symbol: holding.symbol,
      weight: Number(holding.target_allocation)
    })) ?? []
    : holdingMode === 'real'
      ? portfolioState.valuation?.holdings.map((holding) => ({
        symbol: holding.symbol,
        weight: Number(holding.current_allocation)
      })) ?? []
      : portfolioState.portfolio?.holdings.flatMap((holding) => holding.weight === null
        ? []
        : [{ symbol: holding.symbol, weight: holding.weight }]) ?? [];

  useEffect(() => {
    if (!scenarios.length) {
      setScenarioId(null);
    } else if (!scenarioId || !scenarios.some((scenario) => scenario.id === scenarioId)) {
      setScenarioId(scenarios[0].id);
    }
  }, [scenarioId, scenarios]);

  useEffect(() => {
    const requestId = latestAnalysisRequestRef.current + 1;
    latestAnalysisRequestRef.current = requestId;
    setLatestAnalysis(null);
    setLatestAnalysisError(null);
    if (!selectedPortfolioSummary) {
      setLatestAnalysisStatus('idle');
      return;
    }

    setLatestAnalysisStatus('loading');
    void getPortfolioReportHistory(selectedPortfolioSummary)
      .then(async (history) => {
        const newest = history[0];
        if (!newest) return null;
        return getReport(selectedPortfolioSummary.id, newest.id);
      })
      .then((report) => {
        if (latestAnalysisRequestRef.current !== requestId) return;
        setLatestAnalysis(report);
        setLatestAnalysisStatus('ready');
      })
      .catch((error: unknown) => {
        if (latestAnalysisRequestRef.current !== requestId) return;
        setLatestAnalysisError(error);
        setLatestAnalysisStatus('error');
      });
    return () => {
      if (latestAnalysisRequestRef.current === requestId) {
        latestAnalysisRequestRef.current += 1;
      }
    };
  }, [getPortfolioReportHistory, getReport, selectedPortfolioSummary]);

  async function run() {
    if (runningRef.current || !portfolioState.portfolio || !scenarioId) return;
    runningRef.current = true;
    setRunning(true);
    setRunError(null);
    setRunFailure(null);
    try {
      const response = await runHistorical(portfolioState.portfolio.id, scenarioId);
      setResult({ type: 'historical-scenario', response });
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

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Historical Scenario</Text>
        <Text style={styles.subtitle}>See how a saved portfolio would have performed during a historical event.</Text>

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
              <InlineErrorCard
                error={portfolioFailure}
                message={portfolioErrorMessage(portfolioFailure)}
                stale={Boolean(portfolioState.portfolio)}
                onRetry={() => void (portfolioState.listStatus === 'error'
                  ? portfolioState.refreshPortfolios()
                  : portfolioState.retryPortfolio())}
                retryTitle="Retry portfolio"
              />
            ) : null}
            {portfolioState.valuationStatus === 'loading' ? (
              <Text style={styles.state}>{holdingMode === 'planned'
                ? 'Loading the original target allocation…'
                : 'Loading the original current USD allocation…'}</Text>
            ) : null}
            {portfolioState.valuationStatus === 'error' ? (
              <InlineErrorCard
                error={portfolioState.valuationError}
                message={holdingMode === 'planned'
                  ? portfolioErrorMessage(portfolioState.valuationError, 'Unable to load the original planned allocation.')
                  : portfolioValuationErrorMessage(portfolioState.valuationError)}
                onRetry={() => void portfolioState.retryPortfolio()}
                retryTitle="Retry original allocation"
              />
            ) : null}

            <Text style={styles.section}>Scenario</Text>
            {scenarioStatus === 'loading' && !scenarios.length ? <Text style={styles.state}>Loading historical scenarios…</Text> : null}
            {scenarioStatus === 'error' ? (
              <InlineErrorCard
                error={scenarioError}
                message={simulationErrorMessage(scenarioError, 'Unable to load historical scenarios.')}
                stale={Boolean(scenarios.length)}
                onRetry={() => void refreshScenarios()}
                retryTitle="Retry scenarios"
              />
            ) : scenarios.length ? (
              <ScenarioSelector disabled={running} scenarios={scenarios} selectedId={scenarioId} onSelect={(id) => { if (runningRef.current) return; setScenarioId(id); setResult(null); }} />
            ) : scenarioStatus === 'ready' ? (
              <Card><EmptyState title="No scenarios available" description="Aura could not find any historical scenarios." /></Card>
            ) : null}

            {runError ? <FormErrorSummary error={runFailure} message={runError} /> : null}
            {portfolioState.portfolio && !portfolioState.portfolio.holdings.length ? <Text style={styles.state}>Add saved holdings before running a simulation.</Text> : null}
            <Button
              title={running ? 'Running…' : 'Run historical scenario'}
              onPress={() => void run()}
              disabled={running || !portfolioState.portfolio?.holdings.length || !scenarioId || scenarioStatus !== 'ready' || !baselineReady}
              style={{ marginTop: spacing.xl }}
            />
            {result ? <SimulationResults
              result={result}
              originalAllocation={originalAllocation}
              latestAnalysis={latestAnalysis}
              latestAnalysisStatus={latestAnalysisStatus}
              latestAnalysisError={latestAnalysisError
                ? reportErrorMessage(latestAnalysisError, 'Latest analysis details could not be loaded.')
                : null}
              onViewLatestAnalysis={latestAnalysis ? () => navigation.getParent()?.navigate('MoreTab', {
                screen: 'ReportDetail',
                params: {
                  portfolioId: latestAnalysis.portfolio_id,
                  reportId: latestAnalysis.id
                }
              }) : undefined}
            /> : null}
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
