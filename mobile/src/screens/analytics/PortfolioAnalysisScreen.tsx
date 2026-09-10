import React, { useEffect, useRef, useState } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { AnalysisResults } from '../../components/analytics/AnalysisResults';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import {
  DateRangeSelector,
  type DateRange
} from '../../components/ui/DateRangeSelector';
import { EmptyState } from '../../components/ui/EmptyState';
import { LoadingState } from '../../components/ui/LoadingState';
import { KeyboardAwareScrollView } from '../../components/ui/KeyboardAwareScrollView';
import { PageTitle } from '../../components/ui/PageTitle';
import { portfolioErrorMessage } from '../../portfolio/portfolioErrors';
import { usePortfolios } from '../../portfolio/usePortfolios';
import { reportErrorMessage } from '../../report/reportErrors';
import { formatReportTimestamp } from '../../report/reportFormatting';
import { useReports } from '../../report/useReports';
import { colors, spacing } from '../../theme/theme';
import type { PortfolioReportResponse } from '../../types/report';

function localIsoDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function periodFor(range: DateRange): { start: string; end: string } {
  const months = { '1M': 1, '3M': 3, '6M': 6, '1Y': 12 }[range];
  const end = new Date();
  const originalDay = end.getDate();
  const start = new Date(end.getFullYear(), end.getMonth() - months, 1);
  const lastDay = new Date(
    start.getFullYear(),
    start.getMonth() + 1,
    0
  ).getDate();
  start.setDate(Math.min(originalDay, lastDay));
  return { start: localIsoDate(start), end: localIsoDate(end) };
}

function isIsoDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split('-').map(Number);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return parsed.getUTCFullYear() === year
    && parsed.getUTCMonth() === month - 1
    && parsed.getUTCDate() === day;
}

export function PortfolioAnalysisScreen({
  route,
  navigation
}: {
  route: any;
  navigation: any;
}) {
  const initialPeriod = useRef(periodFor('1Y')).current;
  const requestedPortfolioId = route.params?.portfolioId as string | undefined;
  const {
    portfolios,
    activePortfolioId,
    listStatus,
    listError,
    refreshPortfolios,
    selectPortfolio
  } = usePortfolios();
  const { createReport } = useReports();
  const [selectedPortfolioId, setSelectedPortfolioId] = useState(
    requestedPortfolioId ?? ''
  );
  const [startDate, setStartDate] = useState(initialPeriod.start);
  const [endDate, setEndDate] = useState(initialPeriod.end);
  const [selectedRange, setSelectedRange] = useState<DateRange | null>('1Y');
  const [report, setReport] = useState<PortfolioReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const submittingRef = useRef(false);
  const requestedSelectionHandledRef = useRef(false);

  useEffect(() => {
    if (listStatus !== 'ready') return;

    if (requestedPortfolioId && !requestedSelectionHandledRef.current) {
      requestedSelectionHandledRef.current = true;
      if (portfolios.some((item) => item.id === requestedPortfolioId)) {
        setSelectedPortfolioId(requestedPortfolioId);
        selectPortfolio(requestedPortfolioId);
      } else {
        setSelectedPortfolioId('');
        setError('The requested portfolio was not found.');
      }
      return;
    }

    const currentIsValid = portfolios.some(
      (item) => item.id === selectedPortfolioId
    );
    if (currentIsValid) return;

    const nextId = (
      activePortfolioId
      && portfolios.some((item) => item.id === activePortfolioId)
    ) ? activePortfolioId : portfolios[0]?.id ?? '';
    setSelectedPortfolioId(nextId);
    if (nextId) selectPortfolio(nextId);
  }, [
    activePortfolioId,
    listStatus,
    portfolios,
    requestedPortfolioId,
    selectPortfolio,
    selectedPortfolioId
  ]);

  function choosePortfolio(portfolioId: string) {
    if (analyzing) return;
    setSelectedPortfolioId(portfolioId);
    selectPortfolio(portfolioId);
    setReport(null);
    setError(null);
  }

  function chooseRange(range: DateRange) {
    if (analyzing) return;
    const period = periodFor(range);
    setSelectedRange(range);
    setStartDate(period.start);
    setEndDate(period.end);
    setReport(null);
    setError(null);
  }

  function editStartDate(value: string) {
    setSelectedRange(null);
    setStartDate(value);
    setReport(null);
    setError(null);
  }

  function editEndDate(value: string) {
    setSelectedRange(null);
    setEndDate(value);
    setReport(null);
    setError(null);
  }

  async function analyze() {
    if (submittingRef.current) return;
    if (!selectedPortfolioId) {
      setError('Choose a portfolio to analyze.');
      return;
    }
    if (!startDate.trim() || !endDate.trim()) {
      setError('Enter both the analysis start date and end date.');
      return;
    }
    if (!isIsoDate(startDate) || !isIsoDate(endDate)) {
      setError('Enter valid dates in YYYY-MM-DD format.');
      return;
    }
    if (startDate > endDate) {
      setError('Start date must be on or before end date.');
      return;
    }

    submittingRef.current = true;
    setAnalyzing(true);
    setError(null);
    setReport(null);
    try {
      setReport(await createReport(selectedPortfolioId, {
        start_date: startDate,
        end_date: endDate
      }));
    } catch (requestError) {
      setError(reportErrorMessage(
        requestError,
        'Unable to analyze this portfolio.'
      ));
    } finally {
      submittingRef.current = false;
      setAnalyzing(false);
    }
  }

  if (
    (listStatus === 'idle' || listStatus === 'loading')
    && !portfolios.length
  ) {
    return <LoadingState message="Loading portfolios…" />;
  }

  if (listStatus === 'error' && !portfolios.length) {
    return (
      <SafeAreaView style={styles.safe} edges={['bottom']}>
        <View style={styles.centerState}>
          <Card style={styles.stateCard}>
            <Text style={styles.errorTitle}>Portfolios unavailable</Text>
            <Text style={styles.stateText}>{portfolioErrorMessage(listError)}</Text>
            <Button title="Retry" onPress={() => void refreshPortfolios()} />
          </Card>
        </View>
      </SafeAreaView>
    );
  }

  if (listStatus === 'ready' && !portfolios.length) {
    return (
      <SafeAreaView style={styles.safe} edges={['bottom']}>
        <View style={styles.centerState}>
          <Card>
            <EmptyState
              icon="analytics-outline"
              title="No portfolio to analyze"
              description="Create a real portfolio and complete its holdings before running analysis."
            />
          </Card>
        </View>
      </SafeAreaView>
    );
  }

  const selectedPortfolio = portfolios.find(
    (item) => item.id === selectedPortfolioId
  );

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <KeyboardAwareScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
      >
        <PageTitle
          eyebrow="PORTFOLIO ANALYSIS"
          title="Analytics"
          subtitle="Run Aura's backend analytics and save one immutable report."
        />

        {listStatus === 'error' ? (
          <Card style={styles.stateCard}>
            <Text style={styles.errorTitle}>Portfolio list refresh failed</Text>
            <Text style={styles.stateText}>Using the previously loaded portfolios. {portfolioErrorMessage(listError)}</Text>
            <Button title="Retry portfolios" onPress={() => void refreshPortfolios()} />
          </Card>
        ) : null}

        <Card style={styles.controlsCard}>
          <Text style={styles.controlLabel}>Portfolio</Text>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.portfolioOptions}
          >
            {portfolios.map((portfolio) => {
              const selected = portfolio.id === selectedPortfolioId;
              return (
                <Pressable
                  key={portfolio.id}
                  onPress={() => choosePortfolio(portfolio.id)}
                  disabled={analyzing}
                  style={[styles.portfolioOption, selected && styles.selectedOption]}
                >
                  <Text style={[
                    styles.portfolioName,
                    selected && styles.selectedOptionText
                  ]}>
                    {portfolio.name}
                  </Text>
                </Pressable>
              );
            })}
          </ScrollView>

          <View style={styles.periodHeader}>
            <Text style={styles.controlLabel}>Analysis period</Text>
            <Text style={styles.helper}>Inclusive calendar dates</Text>
          </View>
          <DateRangeSelector value={selectedRange} onChange={chooseRange} />

          <View style={styles.dateRow}>
            <View style={styles.dateField}>
              <Text style={styles.dateLabel}>Start date</Text>
              <TextInput
                value={startDate}
                onChangeText={editStartDate}
                placeholder="YYYY-MM-DD"
                placeholderTextColor={colors.muted}
                autoCapitalize="none"
                keyboardType="numbers-and-punctuation"
                editable={!analyzing}
                style={styles.input}
              />
            </View>
            <View style={styles.dateField}>
              <Text style={styles.dateLabel}>End date</Text>
              <TextInput
                value={endDate}
                onChangeText={editEndDate}
                placeholder="YYYY-MM-DD"
                placeholderTextColor={colors.muted}
                autoCapitalize="none"
                keyboardType="numbers-and-punctuation"
                editable={!analyzing}
                style={styles.input}
              />
            </View>
          </View>

          <Button
            title={analyzing ? 'Analyzing and Saving…' : 'Analyze Portfolio'}
            onPress={() => void analyze()}
            disabled={analyzing || !selectedPortfolioId}
          />
        </Card>

        {error ? (
          <Card style={styles.errorCard}>
            <Text style={styles.errorTitle}>Analysis unavailable</Text>
            <Text style={styles.stateText}>{error}</Text>
          </Card>
        ) : null}

        {analyzing ? (
          <Card style={styles.stateCard}>
            <Text style={styles.stateTitle}>Running portfolio analysis</Text>
            <Text style={styles.stateText}>
              Aura is calculating the requested period and saving the backend report snapshot.
            </Text>
          </Card>
        ) : null}

        {report && !analyzing ? (
          <>
            <Card style={styles.savedCard}>
              <Text style={styles.savedTitle}>Report saved</Text>
              <Text style={styles.savedText}>
                Created {formatReportTimestamp(report.created_at)} for {selectedPortfolio?.name ?? report.analysis.portfolio_name}.
              </Text>
              <Button
                title="Open Immutable Report"
                variant="secondary"
                onPress={() => navigation.navigate('ReportDetail', {
                  portfolioId: report.portfolio_id,
                  reportId: report.id
                })}
              />
            </Card>
            <AnalysisResults analysis={report.analysis} />
          </>
        ) : null}
      </KeyboardAwareScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 110 },
  controlsCard: { gap: spacing.md, marginTop: spacing.xl },
  controlLabel: { color: colors.text, fontSize: 12, fontWeight: '900' },
  helper: { color: colors.muted, fontSize: 9 },
  portfolioOptions: { gap: spacing.sm, paddingRight: spacing.md },
  portfolioOption: {
    minHeight: 42,
    maxWidth: 190,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceAlt
  },
  selectedOption: {
    borderColor: colors.primary,
    backgroundColor: colors.selectedBackground
  },
  portfolioName: { color: colors.textSecondary, fontSize: 11, fontWeight: '800' },
  selectedOptionText: { color: colors.primary },
  periodHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: spacing.sm
  },
  dateRow: { flexDirection: 'row', gap: spacing.md },
  dateField: { flex: 1 },
  dateLabel: { color: colors.muted, fontSize: 10, marginBottom: 6 },
  input: {
    minHeight: 46,
    borderRadius: 13,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceAlt,
    color: colors.text,
    paddingHorizontal: spacing.md,
    fontSize: 12,
    fontWeight: '700'
  },
  errorCard: { gap: spacing.sm, marginTop: spacing.md, borderColor: colors.dangerBorder },
  errorTitle: { color: colors.danger, fontSize: 15, fontWeight: '900' },
  stateCard: { gap: spacing.md, marginTop: spacing.md },
  stateTitle: { color: colors.text, fontSize: 15, fontWeight: '900' },
  stateText: { color: colors.textSecondary, fontSize: 12, lineHeight: 18 },
  savedCard: { gap: spacing.md, marginTop: spacing.xl, borderColor: colors.successBorder },
  savedTitle: { color: colors.success, fontSize: 16, fontWeight: '900' },
  savedText: { color: colors.textSecondary, fontSize: 11, lineHeight: 17 },
  centerState: { flex: 1, justifyContent: 'center', padding: spacing.xl }
});
