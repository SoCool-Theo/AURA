import React, { useCallback, useMemo, useState } from 'react';
import {
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  View
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';

import { PortfolioCard } from '../../components/portfolio/PortfolioCard';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { InlineErrorCard, ScreenErrorState } from '../../components/ui/ErrorState';
import { LoadingState } from '../../components/ui/LoadingState';
import { KeyboardAwareScrollView } from '../../components/ui/KeyboardAwareScrollView';
import { PageTitle } from '../../components/ui/PageTitle';
import { portfolioErrorMessage } from '../../portfolio/portfolioErrors';
import { usePortfolios } from '../../portfolio/usePortfolios';
import { reportErrorMessage } from '../../report/reportErrors';
import { useReports } from '../../report/useReports';
import { colors, spacing } from '../../theme/theme';

export function PortfoliosScreen({ navigation }: { navigation: any }) {
  const {
    portfolios,
    activePortfolioId,
    listStatus,
    listError,
    isRefreshing,
    refreshPortfolios,
    selectPortfolio
  } = usePortfolios();
  const {
    reports,
    historyStatus,
    historyError,
    refreshReportHistory
  } = useReports();
  const [query, setQuery] = useState('');

  useFocusEffect(useCallback(() => {
    if ((listStatus === 'ready' || portfolios.length) && portfolios.length) {
      void refreshReportHistory(portfolios);
    }
  }, [listStatus, portfolios, refreshReportHistory]));

  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) return portfolios;
    return portfolios.filter((portfolio) => (
      portfolio.name.toLowerCase().includes(normalizedQuery)
    ));
  }, [portfolios, query]);

  const latestReportByPortfolio = useMemo(() => {
    const latest = new Map<string, (typeof reports)[number]>();
    for (const report of reports) {
      if (!latest.has(report.portfolio_id)) {
        latest.set(report.portfolio_id, report);
      }
    }
    return latest;
  }, [reports]);

  if (
    (listStatus === 'idle' || listStatus === 'loading')
    && !portfolios.length
  ) {
    return <LoadingState message="Loading portfolios…" />;
  }

  if (listStatus === 'error' && !portfolios.length) {
    return (
      <SafeAreaView style={styles.safe}>
        <ScreenErrorState
          error={listError}
          resourceName="Portfolio list"
          fallbackMessage="Unable to load your portfolios."
          onRetry={() => void refreshPortfolios()}
        />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAwareScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        refreshControl={(
          <RefreshControl
            refreshing={isRefreshing}
            onRefresh={() => void refreshPortfolios()}
            tintColor={colors.primary}
          />
        )}
      >
        <PageTitle
          title="My Portfolios"
          subtitle="Create and manage your saved portfolio allocations."
          right={(
            <Pressable
              accessibilityLabel="Create portfolio"
              accessibilityRole="button"
              style={styles.newButton}
              onPress={() => navigation.navigate('CreatePortfolio')}
            >
              <Ionicons name="add" size={19} color={colors.onPrimary} />
            </Pressable>
          )}
        />

        {listStatus === 'error' ? (
          <InlineErrorCard
            error={listError}
            message={portfolioErrorMessage(listError)}
            stale
            onRetry={() => void refreshPortfolios()}
          />
        ) : null}

        {historyStatus === 'error' ? (
          <InlineErrorCard
            error={historyError}
            message={reportErrorMessage(historyError, 'Unable to check portfolio report history.')}
            stale={Boolean(reports.length)}
            onRetry={() => void refreshReportHistory(portfolios)}
            retryTitle="Retry reports"
          />
        ) : null}

        {(historyStatus === 'idle' || historyStatus === 'loading')
          && portfolios.length ? (
            <Text style={styles.reportStatus}>Checking saved reports…</Text>
          ) : null}

        {portfolios.length ? (
          <View style={styles.searchBar}>
            <Ionicons name="search-outline" size={17} color={colors.muted} />
            <TextInput
              accessibilityLabel="Search portfolios"
              value={query}
              onChangeText={setQuery}
              placeholder="Search portfolios"
              placeholderTextColor={colors.muted}
              style={styles.searchInput}
            />
          </View>
        ) : null}

        {listStatus !== 'error' && !portfolios.length ? (
          <Card style={styles.emptyCard}>
            <EmptyState
              title="No portfolios yet"
              description="Create a current portfolio for assets you own or a planned portfolio to evaluate before investing."
            />
          </Card>
        ) : filtered.length ? (
          <View style={styles.list}>
            {filtered.map((portfolio) => (
              <PortfolioCard
                key={portfolio.id}
                portfolio={portfolio}
                active={portfolio.id === activePortfolioId}
                onPress={() => {
                  selectPortfolio(portfolio.id);
                  navigation.navigate('PortfolioDetail', {
                    portfolioId: portfolio.id
                  });
                }}
                onOpenReport={latestReportByPortfolio.has(portfolio.id)
                  ? () => {
                    const report = latestReportByPortfolio.get(portfolio.id);
                    if (!report) return;
                    navigation.navigate('ReportDetail', {
                      portfolioId: portfolio.id,
                      reportId: report.id
                    });
                  }
                  : undefined}
              />
            ))}
          </View>
        ) : portfolios.length ? (
          <Card style={styles.emptyCard}>
            <EmptyState
              icon="search-outline"
              title="No matching portfolios"
              description="Try a different portfolio name."
            />
          </Card>
        ) : null}

        <Pressable
          accessibilityLabel="Create portfolio"
          accessibilityRole="button"
          onPress={() => navigation.navigate('CreatePortfolio')}
        >
          <Card style={styles.createCta}>
            <View style={{ flex: 1 }}>
              <Text style={styles.ctaEyebrow}>CREATE NEW PORTFOLIO</Text>
              <Text style={styles.ctaTitle}>
                Record current holdings or proposed amounts and let Aura calculate the appropriate allocation.
              </Text>
              <View style={styles.ctaLink}>
                <Ionicons name="add-circle-outline" size={16} color={colors.primary} />
                <Text style={styles.ctaLinkText}>Create Portfolio</Text>
              </View>
            </View>
          </Card>
        </Pressable>
      </KeyboardAwareScrollView>
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
  errorCard: { gap: spacing.md, marginTop: spacing.xl },
  errorTitle: { color: colors.danger, fontSize: 15, fontWeight: '900' },
  errorText: { color: colors.textSecondary, fontSize: 12, lineHeight: 18 },
  searchBar: {
    height: 44,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    borderRadius: 13,
    backgroundColor: colors.surfaceAlt,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    marginTop: spacing.xl
  },
  searchInput: { flex: 1, color: colors.text, fontSize: 12 },
  reportStatus: { color: colors.textSecondary, fontSize: 11, marginTop: spacing.md },
  list: { gap: spacing.md, marginTop: spacing.xl },
  emptyCard: { marginTop: spacing.xl },
  createCta: {
    marginTop: spacing.xl,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xl,
    borderStyle: 'dashed',
    borderColor: colors.primary
  },
  ctaEyebrow: {
    color: colors.primary,
    fontSize: 9,
    fontWeight: '900',
    letterSpacing: 1
  },
  ctaTitle: {
    color: colors.text,
    fontSize: 17,
    fontWeight: '900',
    lineHeight: 22,
    marginTop: 6
  },
  ctaLink: {
    flexDirection: 'row',
    gap: 6,
    alignItems: 'center',
    marginTop: spacing.md
  },
  ctaLinkText: { color: colors.primary, fontSize: 11, fontWeight: '900' }
});
