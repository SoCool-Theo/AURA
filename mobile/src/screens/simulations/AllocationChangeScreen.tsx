import React, { useEffect, useRef, useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { AllocationEditor } from '../../components/simulations/AllocationEditor';
import { PortfolioSelector } from '../../components/simulations/PortfolioSelector';
import { SimulationResults } from '../../components/simulations/SimulationResults';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { LoadingState } from '../../components/ui/LoadingState';
import { KeyboardAwareScrollView } from '../../components/ui/KeyboardAwareScrollView';
import { portfolioErrorMessage } from '../../portfolio/portfolioErrors';
import { simulationErrorMessage } from '../../simulation/simulationErrors';
import type { SimulationRunResult } from '../../simulation/SimulationProvider';
import {
  allocationInputsFromPortfolio,
  allocationTotal,
  defaultSimulationPeriod,
  isValidIsoDate,
  validateModifiedAllocation,
  type AllocationInputs
} from '../../simulation/simulationValidation';
import { useSimulationPortfolio } from '../../simulation/useSimulationPortfolio';
import { useSimulations } from '../../simulation/useSimulations';
import { colors, spacing, typography } from '../../theme/theme';

export function AllocationChangeScreen({ route }: { route: any }) {
  const portfolioState = useSimulationPortfolio(route.params?.portfolioId);
  const { runAllocation } = useSimulations();
  const initialPeriod = useRef(defaultSimulationPeriod()).current;
  const [startDate, setStartDate] = useState(initialPeriod.start);
  const [endDate, setEndDate] = useState(initialPeriod.end);
  const [weights, setWeights] = useState<AllocationInputs>({});
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [result, setResult] = useState<SimulationRunResult | null>(null);
  const runningRef = useRef(false);

  useEffect(() => {
    if (portfolioState.portfolio) {
      setWeights(allocationInputsFromPortfolio(portfolioState.portfolio));
      setResult(null);
      setRunError(null);
    }
  }, [portfolioState.portfolio]);

  async function run() {
    const portfolio = portfolioState.portfolio;
    if (runningRef.current || !portfolio) return;
    if (!isValidIsoDate(startDate) || !isValidIsoDate(endDate) || startDate > endDate) {
      setRunError('Enter a valid start and end date in YYYY-MM-DD format, with the start no later than the end.');
      return;
    }
    const validated = validateModifiedAllocation(portfolio, weights);
    if (!validated.allocation) {
      setRunError(validated.error);
      return;
    }

    runningRef.current = true;
    setRunning(true);
    setRunError(null);
    try {
      const response = await runAllocation(portfolio.id, {
        start_date: startDate,
        end_date: endDate,
        modified_allocation: validated.allocation
      });
      setResult({ type: 'allocation', response });
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
      <KeyboardAwareScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Allocation Change</Text>
        <Text style={styles.subtitle}>Compare the saved portfolio with a modified allocation over an explicit period.</Text>

        {!portfolioState.portfolios.length ? (
          <Card><EmptyState title="No portfolio available" description="Create a portfolio with holdings before running a simulation." /></Card>
        ) : (
          <>
            <Text style={styles.section}>Portfolio</Text>
            <PortfolioSelector disabled={running} portfolios={portfolioState.portfolios} selectedId={portfolioState.selectedPortfolioId} onSelect={(id) => { if (!runningRef.current) portfolioState.choosePortfolio(id); }} />
            {portfolioState.detailStatus === 'loading' ? <Text style={styles.state}>Loading holdings…</Text> : null}
            {portfolioFailure ? (
              <Card style={styles.errorCard}><Text style={styles.error}>{portfolioFailure}</Text><Button title="Retry portfolio" onPress={() => void (portfolioState.listStatus === 'error' ? portfolioState.refreshPortfolios() : portfolioState.retryPortfolio())} /></Card>
            ) : null}
            {portfolioState.portfolio && !portfolioState.portfolio.holdings.length ? (
              <Card><EmptyState title="No holdings available" description="Add holdings to this portfolio before changing its allocation." /></Card>
            ) : portfolioState.portfolio ? (
              <>
                <Text style={styles.section}>Analysis period</Text>
                <View style={styles.dateRow}>
                  <View style={styles.dateField}><Text style={styles.label}>START</Text><TextInput editable={!running} value={startDate} onChangeText={setStartDate} style={styles.dateInput} placeholder="YYYY-MM-DD" placeholderTextColor={colors.muted} /></View>
                  <View style={styles.dateField}><Text style={styles.label}>END</Text><TextInput editable={!running} value={endDate} onChangeText={setEndDate} style={styles.dateInput} placeholder="YYYY-MM-DD" placeholderTextColor={colors.muted} /></View>
                </View>
                <Text style={styles.section}>Modified allocation</Text>
                <AllocationEditor disabled={running} portfolio={portfolioState.portfolio} inputs={weights} total={allocationTotal(weights)} onChange={(symbol, value) => setWeights((current) => ({ ...current, [symbol]: value }))} />
                {runError ? <Card style={styles.errorCard}><Text style={styles.error}>{runError}</Text></Card> : null}
                <Button title={running ? 'Running…' : 'Compare allocation'} onPress={() => void run()} disabled={running} style={{ marginTop: spacing.xl }} />
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
  dateRow: { flexDirection: 'row', gap: spacing.md },
  dateField: { flex: 1 },
  label: { color: colors.muted, fontSize: 9, fontWeight: '900', marginBottom: spacing.xs },
  dateInput: { minHeight: 46, borderRadius: 13, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surfaceAlt, color: colors.text, paddingHorizontal: spacing.md },
  errorCard: { gap: spacing.md, borderColor: colors.dangerBorder, marginTop: spacing.md },
  error: { color: colors.danger, lineHeight: 18, fontSize: 12 }
});
