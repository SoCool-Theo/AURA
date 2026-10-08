import React, { useCallback, useMemo, useRef, useState } from 'react';
import {
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';

import { Card } from '../../components/ui/Card';
import { ConfirmationDialog } from '../../components/ui/ConfirmationDialog';
import { EmptyState } from '../../components/ui/EmptyState';
import { InlineErrorCard, ScreenErrorState } from '../../components/ui/ErrorState';
import { LoadingState } from '../../components/ui/LoadingState';
import { KeyboardAwareScrollView } from '../../components/ui/KeyboardAwareScrollView';
import { PageTitle } from '../../components/ui/PageTitle';
import { Tag } from '../../components/ui/Tag';
import { portfolioErrorMessage } from '../../portfolio/portfolioErrors';
import { usePortfolios } from '../../portfolio/usePortfolios';
import { reportErrorMessage } from '../../report/reportErrors';
import { formatReportTimestamp } from '../../report/reportFormatting';
import { useReports } from '../../report/useReports';
import type { ReportHistoryItem } from '../../report/ReportProvider';
import { colors, spacing } from '../../theme/theme';

export function ReportsScreen({ navigation }: { navigation: any }) {
  const {
    portfolios,
    listStatus,
    listError,
    refreshPortfolios
  } = usePortfolios();
  const {
    reports,
    historyStatus,
    historyError,
    isRefreshing,
    refreshReportHistory,
    deleteReport
  } = useReports();
  const [query, setQuery] = useState('');
  const [portfolioFilter, setPortfolioFilter] = useState('');
  const [actionError, setActionError] = useState<unknown>(null);
  const deletingIdsRef = useRef(new Set<string>());
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set());
  const [reportToDelete, setReportToDelete] = useState<ReportHistoryItem | null>(null);

  useFocusEffect(useCallback(() => {
    if (listStatus === 'ready' || portfolios.length) {
      void refreshReportHistory(portfolios);
    }
  }, [listStatus, portfolios, refreshReportHistory]));

  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return reports.filter((report) => (
      (!portfolioFilter || report.portfolio_id === portfolioFilter)
      && (
        !normalizedQuery
        || report.portfolio_name.toLowerCase().includes(normalizedQuery)
        || report.id.toLowerCase().includes(normalizedQuery)
      )
    ));
  }, [portfolioFilter, query, reports]);

  function retry() {
    if (listStatus === 'error') {
      void refreshPortfolios();
      return;
    }
    void refreshReportHistory(portfolios);
  }

  function confirmDelete(report: ReportHistoryItem) {
    if (deletingIdsRef.current.has(report.id)) return;
    setActionError(null);
    setReportToDelete(report);
  }

  async function submitDelete() {
    const report = reportToDelete;
    if (!report || deletingIdsRef.current.has(report.id)) return;
    deletingIdsRef.current.add(report.id);
    setDeletingIds(new Set(deletingIdsRef.current));
    setActionError(null);
    try {
      await deleteReport(report.portfolio_id, report.id);
      setReportToDelete(null);
    } catch (error) {
      setActionError(error);
    } finally {
      deletingIdsRef.current.delete(report.id);
      setDeletingIds(new Set(deletingIdsRef.current));
    }
  }

  if (
    ((listStatus === 'idle' || listStatus === 'loading') && !portfolios.length)
    || (historyStatus === 'idle' || historyStatus === 'loading')
      && !reports.length
      && listStatus !== 'error'
  ) {
    return <LoadingState message="Loading report history…" />;
  }

  const blockingError = listStatus === 'error' && !portfolios.length
    ? listError
    : historyStatus === 'error' && !reports.length
      ? historyError
      : null;

  if (blockingError) {
    return (
      <SafeAreaView style={styles.safe} edges={['bottom']}>
        <ScreenErrorState
          error={blockingError}
          resourceName="Report history"
          fallbackMessage="Unable to load report history."
          onRetry={retry}
        />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <KeyboardAwareScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        refreshControl={(
          <RefreshControl
            refreshing={isRefreshing}
            onRefresh={retry}
            tintColor={colors.primary}
          />
        )}
      >
        <PageTitle
          title="Reports"
          subtitle="Saved analysis results, newest first."
          right={(
            <Pressable
              accessibilityLabel="Create report"
              accessibilityRole="button"
              style={styles.newButton}
              onPress={() => navigation.navigate('Analytics', {})}
            >
              <Ionicons name="add" size={19} color={colors.onPrimary} />
            </Pressable>
          )}
        />

        {actionError ? (
          <InlineErrorCard
            error={actionError}
            message={reportErrorMessage(actionError, 'Unable to delete report.')}
          />
        ) : null}

        {listStatus === 'error' && portfolios.length ? (
          <InlineErrorCard
            error={listError}
            message={portfolioErrorMessage(listError)}
            stale
            retryTitle="Retry portfolios"
            onRetry={retry}
          />
        ) : null}

        {historyStatus === 'error' && reports.length ? (
          <InlineErrorCard
            error={historyError}
            message={reportErrorMessage(historyError, 'Unable to refresh report history.')}
            stale
            onRetry={retry}
          />
        ) : null}

        {reports.length ? (
          <>
            <View style={styles.search}>
              <Ionicons name="search-outline" color={colors.muted} size={17} />
              <TextInput
                accessibilityLabel="Search reports"
                value={query}
                onChangeText={setQuery}
                placeholder="Search portfolio name or report ID"
                placeholderTextColor={colors.muted}
                style={styles.searchInput}
              />
            </View>

            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.filterRow}
            >
              <Pressable
                accessibilityLabel="All portfolios report filter"
                accessibilityRole="radio"
                accessibilityState={{ selected: !portfolioFilter }}
                onPress={() => setPortfolioFilter('')}
                style={styles.filterOption}
              >
                <Tag label="All portfolios" tone={!portfolioFilter ? 'primary' : 'default'} />
              </Pressable>
              {portfolios.map((portfolio) => (
                <Pressable
                  accessibilityLabel={`${portfolio.name} report filter`}
                  accessibilityRole="radio"
                  accessibilityState={{ selected: portfolioFilter === portfolio.id }}
                  key={portfolio.id}
                  onPress={() => setPortfolioFilter(portfolio.id)}
                  style={styles.filterOption}
                >
                  <Tag
                    label={portfolio.name}
                    tone={portfolioFilter === portfolio.id ? 'primary' : 'default'}
                  />
                </Pressable>
              ))}
            </ScrollView>
          </>
        ) : null}

        <View style={styles.list}>
          {!reports.length ? (
            <Card>
              <EmptyState
                icon="document-text-outline"
                title="No reports yet"
                description="Run an analysis to create your first saved report."
              />
            </Card>
          ) : filtered.length ? filtered.map((report) => {
            const deleting = deletingIds.has(report.id);
            return (
              <Pressable
                accessibilityLabel={`Open ${report.portfolio_name} report`}
                accessibilityRole="button"
                accessibilityState={{ disabled: deleting }}
                key={report.id}
                onPress={() => navigation.navigate('ReportDetail', {
                  portfolioId: report.portfolio_id,
                  reportId: report.id
                })}
                disabled={deleting}
              >
                <Card style={styles.reportCard}>
                  <View style={styles.icon}>
                    <Ionicons
                      name="document-text-outline"
                      color={colors.primary}
                      size={22}
                    />
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.title}>{report.portfolio_name} Analysis</Text>
                    <Text style={styles.period}>
                      {report.start_date} → {report.end_date}
                    </Text>
                    <Text style={styles.date}>
                      {formatReportTimestamp(report.created_at)}
                    </Text>
                  </View>
                  <Pressable
                    accessibilityLabel={`Delete ${report.portfolio_name} report`}
                    accessibilityRole="button"
                    accessibilityState={{ disabled: deleting }}
                    onPress={(event) => {
                      event.stopPropagation();
                      confirmDelete(report);
                    }}
                    style={styles.delete}
                    disabled={deleting}
                  >
                    <Ionicons
                      name={deleting ? 'hourglass-outline' : 'trash-outline'}
                      color={deleting ? colors.warning : colors.muted}
                      size={17}
                    />
                  </Pressable>
                </Card>
              </Pressable>
            );
          }) : (
            <Card>
              <EmptyState
                icon="search-outline"
                title="No matching reports"
                description="Change the portfolio filter or search text."
              />
            </Card>
          )}
        </View>

        <Text style={styles.note}>
          Saved reports are read-only. Export, sharing, download, and editing are unavailable.
        </Text>
      </KeyboardAwareScrollView>
      <ConfirmationDialog
        visible={reportToDelete !== null}
        title="Delete report?"
        description="This permanently removes the saved analysis snapshot and cannot be undone."
        subjectLabel="Saved report"
        subject={reportToDelete ? `${reportToDelete.portfolio_name} · ${reportToDelete.id}` : ''}
        confirmLabel="Delete Report"
        busy={Boolean(reportToDelete && deletingIds.has(reportToDelete.id))}
        errorMessage={reportToDelete && actionError ? reportErrorMessage(actionError, 'Unable to delete report.') : null}
        onCancel={() => { if (!reportToDelete || !deletingIds.has(reportToDelete.id)) { setReportToDelete(null); setActionError(null); } }}
        onConfirm={() => void submitDelete()}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 110 },
  newButton: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center'
  },
  search: {
    height: 44,
    borderRadius: 13,
    backgroundColor: colors.surfaceAlt,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    marginTop: spacing.xl
  },
  searchInput: { flex: 1, color: colors.text, fontSize: 12 },
  filterRow: { gap: spacing.sm, paddingVertical: spacing.lg },
  filterOption: { minHeight: 44, justifyContent: 'center' },
  list: { gap: spacing.md, marginTop: spacing.lg },
  reportCard: { flexDirection: 'row', gap: spacing.md, alignItems: 'center' },
  icon: {
    width: 48,
    height: 48,
    borderRadius: 15,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.cyanBackground
  },
  title: { color: colors.text, fontWeight: '900', fontSize: 14 },
  period: { color: colors.textSecondary, fontSize: 10, marginTop: 4 },
  date: { color: colors.muted, fontSize: 9, marginTop: 5 },
  delete: {
    width: 40,
    height: 40,
    borderRadius: 12,
    backgroundColor: colors.surfaceAlt,
    alignItems: 'center',
    justifyContent: 'center'
  },
  errorCard: { gap: spacing.md, marginTop: spacing.xl, borderColor: colors.dangerBorder },
  errorTitle: { color: colors.danger, fontSize: 15, fontWeight: '900' },
  stateCard: { gap: spacing.md },
  stateText: { color: colors.textSecondary, fontSize: 12, lineHeight: 18 },
  centerState: { flex: 1, justifyContent: 'center', padding: spacing.xl },
  note: {
    color: colors.muted,
    fontSize: 10,
    lineHeight: 16,
    textAlign: 'center',
    marginTop: spacing.xl
  }
});
