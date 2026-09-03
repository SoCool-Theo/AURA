import React, { useCallback, useRef, useState } from 'react';
import { Alert, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect } from '@react-navigation/native';

import { AnalysisResults } from '../../components/analytics/AnalysisResults';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { LoadingState } from '../../components/ui/LoadingState';
import { PageTitle } from '../../components/ui/PageTitle';
import { reportErrorMessage } from '../../report/reportErrors';
import { formatReportTimestamp } from '../../report/reportFormatting';
import { useReports } from '../../report/useReports';
import { colors, spacing } from '../../theme/theme';
import type { PortfolioReportResponse } from '../../types/report';

type LoadStatus = 'loading' | 'ready' | 'error';

export function ReportDetailScreen({
  route,
  navigation
}: {
  route: any;
  navigation: any;
}) {
  const portfolioId = route.params.portfolioId as string;
  const reportId = route.params.reportId as string;
  const { getReport, deleteReport } = useReports();
  const [report, setReport] = useState<PortfolioReportResponse | null>(null);
  const [loadStatus, setLoadStatus] = useState<LoadStatus>('loading');
  const [loadError, setLoadError] = useState<unknown>(null);
  const [deleting, setDeleting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const requestRef = useRef(0);
  const deletingRef = useRef(false);

  const loadReport = useCallback(async () => {
    const requestId = requestRef.current + 1;
    requestRef.current = requestId;
    setLoadStatus('loading');
    setLoadError(null);
    setReport(null);

    try {
      const response = await getReport(portfolioId, reportId);
      if (requestRef.current !== requestId) return;
      setReport(response);
      setLoadStatus('ready');
    } catch (error) {
      if (requestRef.current !== requestId) return;
      setLoadError(error);
      setLoadStatus('error');
    }
  }, [getReport, portfolioId, reportId]);

  useFocusEffect(useCallback(() => {
    void loadReport();
    return () => {
      requestRef.current += 1;
    };
  }, [loadReport]));

  function confirmDelete() {
    if (!report || deletingRef.current) return;
    Alert.alert(
      'Delete report?',
      `Permanently delete the saved analysis for ${report.analysis.portfolio_name}?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            if (deletingRef.current) return;
            deletingRef.current = true;
            setDeleting(true);
            setActionError(null);
            try {
              await deleteReport(portfolioId, reportId);
              const navigationState = navigation.getState?.();
              const previousRoute = navigationState?.routes?.[
                navigationState.index - 1
              ]?.name;
              if (
                previousRoute === 'Analytics'
                || previousRoute === 'PortfolioAnalysis'
              ) {
                navigation.popToTop();
              } else {
                navigation.goBack();
              }
            } catch (error) {
              setActionError(reportErrorMessage(
                error,
                'Unable to delete report.'
              ));
              deletingRef.current = false;
              setDeleting(false);
            }
          }
        }
      ]
    );
  }

  if (loadStatus === 'loading') {
    return <LoadingState message="Loading immutable report…" />;
  }

  if (loadStatus === 'error' || !report) {
    return (
      <SafeAreaView style={styles.safe} edges={['bottom']}>
        <View style={styles.centerState}>
          <Card style={styles.stateCard}>
            <Text style={styles.errorTitle}>Report unavailable</Text>
            <Text style={styles.stateText}>
              {reportErrorMessage(loadError, 'Report not found.')}
            </Text>
            <Button title="Retry" onPress={() => void loadReport()} />
            <Button
              title="Back"
              variant="secondary"
              onPress={() => navigation.goBack()}
            />
          </Card>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content}>
        <PageTitle
          eyebrow="IMMUTABLE SNAPSHOT"
          title={`${report.analysis.portfolio_name} Analysis`}
          subtitle={`Created ${formatReportTimestamp(report.created_at)}`}
        />

        <Card style={styles.identityCard}>
          <View style={styles.identityRow}>
            <Text style={styles.identityLabel}>Report ID</Text>
            <Text style={styles.identityValue}>{report.id}</Text>
          </View>
          <View style={styles.identityRow}>
            <Text style={styles.identityLabel}>Portfolio ID</Text>
            <Text style={styles.identityValue}>{report.portfolio_id}</Text>
          </View>
          <Text style={styles.snapshotNote}>
            This detail uses the stored backend report and does not rerun analysis.
          </Text>
        </Card>

        {actionError ? (
          <Card style={styles.errorCard}>
            <Text style={styles.errorTitle}>Unable to delete report</Text>
            <Text style={styles.stateText}>{actionError}</Text>
          </Card>
        ) : null}

        <AnalysisResults analysis={report.analysis} />

        <Button
          title={deleting ? 'Deleting…' : 'Delete Report'}
          variant="danger"
          onPress={confirmDelete}
          disabled={deleting}
          style={{ marginTop: spacing.xl }}
        />
        <Text style={styles.unsupportedNote}>
          Sharing, export, download, and report editing are unavailable.
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 110 },
  identityCard: { gap: spacing.sm, marginTop: spacing.xl },
  identityRow: { flexDirection: 'row', gap: spacing.md },
  identityLabel: { color: colors.muted, fontSize: 9, width: 70 },
  identityValue: { color: colors.text, fontSize: 9, flex: 1 },
  snapshotNote: {
    color: colors.textSecondary,
    fontSize: 11,
    lineHeight: 17,
    marginTop: spacing.sm
  },
  errorCard: { gap: spacing.sm, marginTop: spacing.md, borderColor: colors.dangerBorder },
  errorTitle: { color: colors.danger, fontSize: 15, fontWeight: '900' },
  stateCard: { gap: spacing.md },
  stateText: { color: colors.textSecondary, fontSize: 12, lineHeight: 18 },
  centerState: { flex: 1, justifyContent: 'center', padding: spacing.xl },
  unsupportedNote: {
    color: colors.muted,
    fontSize: 10,
    textAlign: 'center',
    lineHeight: 16,
    marginTop: spacing.md
  }
});
