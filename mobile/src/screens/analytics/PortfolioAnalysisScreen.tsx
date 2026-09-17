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

import { apiValidationIssues } from '../../api/apiErrorPresentation';
import { AnalysisResults } from '../../components/analytics/AnalysisResults';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import {
  DateRangeSelector,
  type DateRange
} from '../../components/ui/DateRangeSelector';
import { EmptyState } from '../../components/ui/EmptyState';
import { FormErrorSummary, InlineErrorCard, ScreenErrorState } from '../../components/ui/ErrorState';
import { LoadingState } from '../../components/ui/LoadingState';
import { KeyboardAwareScrollView } from '../../components/ui/KeyboardAwareScrollView';
import { PageTitle } from '../../components/ui/PageTitle';
import { portfolioErrorMessage } from '../../portfolio/portfolioErrors';
import { usePortfolios } from '../../portfolio/usePortfolios';
import { reportErrorMessage } from '../../report/reportErrors';
import { formatReportTimestamp } from '../../report/reportFormatting';
import { useReports } from '../../report/useReports';
import { colors, spacing } from '../../theme/theme';
import type { PortfolioCurrency } from '../../types/portfolio';
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
  const [currency, setCurrency] = useState<PortfolioCurrency>('USD');
  const [report, setReport] = useState<PortfolioReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [requestError, setRequestError] = useState<unknown>(null);
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
    setRequestError(null);
  }

  function chooseRange(range: DateRange) {
    if (analyzing) return;
    const period = periodFor(range);
    setSelectedRange(range);
    setStartDate(period.start);
    setEndDate(period.end);
    setReport(null);
    setError(null);
    setRequestError(null);
  }

  function editStartDate(value: string) {
    setSelectedRange(null);
    setStartDate(value);
    setReport(null);
    setError(null);
    setRequestError(null);
  }

  function editEndDate(value: string) {
    setSelectedRange(null);
    setEndDate(value);
    setReport(null);
    setError(null);
    setRequestError(null);
  }

  async function analyze() {
    if (submittingRef.current) return;
    if (!selectedPortfolioId) {
      setRequestError(null);
      setError('Choose a portfolio to analyze.');
      return;
    }
    if (!startDate.trim() || !endDate.trim()) {
      setRequestError(null);
      setError('Enter both the analysis start date and end date.');
      return;
    }
    if (!isIsoDate(startDate) || !isIsoDate(endDate)) {
      setRequestError(null);
      setError('Enter valid dates in YYYY-MM-DD format.');
      return;
    }
    if (startDate > endDate) {
      setRequestError(null);
      setError('Start date must be on or before end date.');
      return;
    }

    submittingRef.current = true;
    setAnalyzing(true);
    setError(null);
    setRequestError(null);
    setReport(null);
    try {
      setReport(await createReport(selectedPortfolioId, {
        start_date: startDate,
        end_date: endDate
      }, currency));
    } catch (requestError) {
      setRequestError(requestError);
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
        <ScreenErrorState
          error={listError}
          resourceName="Portfolio list"
          fallbackMessage="Unable to load portfolios for analysis."
          onRetry={() => void refreshPortfolios()}
        />
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
              description="Create a current or planned portfolio and complete its holdings before running analysis."
            />
          </Card>
        </View>
      </SafeAreaView>
    );
  }

  const selectedPortfolio = portfolios.find(
    (item) => item.id === selectedPortfolioId
  );
  const validationIssues = apiValidationIssues(requestError);
  const startDateError = validationIssues.find((issue) => issue.path.endsWith('start_date'))?.message;
  const endDateError = validationIssues.find((issue) => issue.path.endsWith('end_date'))?.message;

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <KeyboardAwareScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
      >
        <PageTitle
          eyebrow="PORTFOLIO ANALYSIS"
          title="Analytics"
          subtitle="Analyze historical risk and save the results."
        />

        {listStatus === 'error' ? (
          <InlineErrorCard
            error={listError}
            message={portfolioErrorMessage(listError)}
            stale
            onRetry={() => void refreshPortfolios()}
            retryTitle="Retry portfolios"
          />
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
                  accessibilityLabel={`${portfolio.name} portfolio`}
                  accessibilityRole="radio"
                  accessibilityState={{ selected, disabled: analyzing }}
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

          {selectedPortfolio?.portfolio_type === 'PLANNED' ? (
            <Card style={styles.plannedNotice}>
              <Text style={styles.controlLabel}>Hypothetical planned analysis</Text>
              <Text style={styles.stateText}>
                Aura analyzes target weights calculated from proposed amounts. Estimated shares are for display only.
              </Text>
            </Card>
          ) : <>
          <View style={styles.periodHeader}>
            <Text style={styles.controlLabel}>Report currency</Text>
            <Text style={styles.helper}>Saved with this report</Text>
          </View>
          <View style={styles.currencyControl}>
            {(['USD', 'THB'] as PortfolioCurrency[]).map((option) => {
              const selected = currency === option;
              return (
                <Pressable
                  accessibilityLabel={`${option} report currency`}
                  accessibilityRole="radio"
                  accessibilityState={{ selected, disabled: analyzing }}
                  disabled={analyzing}
                  key={option}
                  onPress={() => {
                    setCurrency(option);
                    setReport(null);
                    setError(null);
                    setRequestError(null);
                  }}
                  style={[styles.currencyOption, selected && styles.selectedOption]}
                >
                  <Text style={[styles.portfolioName, selected && styles.selectedOptionText]}>{option}</Text>
                </Pressable>
              );
            })}
          </View>
          </>}

          <View style={styles.periodHeader}>
            <Text style={styles.controlLabel}>Analysis period</Text>
            <Text style={styles.helper}>Inclusive calendar dates</Text>
          </View>
          <DateRangeSelector value={selectedRange} onChange={chooseRange} />

          <View style={styles.dateRow}>
            <View style={styles.dateField}>
              <Text style={styles.dateLabel}>Start date</Text>
              <TextInput
                accessibilityLabel="Analysis start date"
                accessibilityState={{ disabled: analyzing }}
                value={startDate}
                onChangeText={editStartDate}
                placeholder="YYYY-MM-DD"
                placeholderTextColor={colors.muted}
                autoCapitalize="none"
                keyboardType="numbers-and-punctuation"
                editable={!analyzing}
                style={[styles.input, startDateError ? styles.inputError : null]}
              />
              {startDateError ? <Text style={styles.fieldError}>{startDateError}</Text> : null}
            </View>
            <View style={styles.dateField}>
              <Text style={styles.dateLabel}>End date</Text>
              <TextInput
                accessibilityLabel="Analysis end date"
                accessibilityState={{ disabled: analyzing }}
                value={endDate}
                onChangeText={editEndDate}
                placeholder="YYYY-MM-DD"
                placeholderTextColor={colors.muted}
                autoCapitalize="none"
                keyboardType="numbers-and-punctuation"
                editable={!analyzing}
                style={[styles.input, endDateError ? styles.inputError : null]}
              />
              {endDateError ? <Text style={styles.fieldError}>{endDateError}</Text> : null}
            </View>
          </View>

          <Button
            title={analyzing ? 'Analyzing and Saving…' : 'Analyze Portfolio'}
            onPress={() => void analyze()}
            disabled={analyzing || !selectedPortfolioId}
          />
        </Card>

        {error ? (
          <FormErrorSummary error={requestError} message={error} />
        ) : null}

        {analyzing ? (
          <Card style={styles.stateCard}>
            <Text style={styles.stateTitle}>Running portfolio analysis</Text>
            <Text style={styles.stateText}>
              Aura is analyzing the requested period and saving the results.
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
                title="Open Saved Report"
                variant="secondary"
                onPress={() => navigation.navigate('ReportDetail', {
                  portfolioId: report.portfolio_id,
                  reportId: report.id
                })}
              />
            </Card>
            <AnalysisResults report={report} />
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
  plannedNotice: { gap: spacing.sm, backgroundColor: colors.summaryBackground, borderColor: colors.primary },
  controlLabel: { color: colors.text, fontSize: 12, fontWeight: '900' },
  helper: { color: colors.muted, fontSize: 9 },
  portfolioOptions: { gap: spacing.sm, paddingRight: spacing.md },
  currencyControl: { flexDirection: 'row', gap: spacing.sm },
  currencyOption: {
    flex: 1,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceAlt
  },
  portfolioOption: {
    minHeight: 44,
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
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: spacing.sm
  },
  dateRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  dateField: { flexGrow: 1, flexBasis: 140 },
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
  inputError: { borderColor: colors.danger },
  fieldError: { color: colors.danger, fontSize: 10, lineHeight: 15, marginTop: 4 },
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
