import React, { useMemo, useState } from 'react';
import { Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { InlineErrorCard, ScreenErrorState } from '../../components/ui/ErrorState';
import { PageTitle } from '../../components/ui/PageTitle';
import { SectionHeader } from '../../components/ui/SectionHeader';
import { WebKpiCard } from '../../components/ui/WebKpiCard';
import { PortfolioReturnsChart } from '../../components/charts/PortfolioReturnsChart';
import { useDashboard } from '../../dashboard/useDashboard';
import { dashboardPercent, filterDashboardReturns, type DashboardRange } from '../../dashboard/dashboardPresentation';
import { usePreferences } from '../../preferences/usePreferences';
import {
  portfolioErrorMessage,
  portfolioValuationErrorMessage
} from '../../portfolio/portfolioErrors';
import { formatPortfolioMoney } from '../../portfolio/portfolioFormatting';
import { reportErrorMessage } from '../../report/reportErrors';
import { formatReportTimestamp, riskTone } from '../../report/reportFormatting';
import { colors, spacing } from '../../theme/theme';
import {
  portfolioHoldingMode,
  type PortfolioCurrency
} from '../../types/portfolio';

const ranges: DashboardRange[] = ['1M', '3M', '6M', '1Y', 'ALL'];

export function DashboardScreen({ navigation }: { navigation: any }) {
  const { displayName } = usePreferences();
  const dashboard = useDashboard();
  const {
    portfoliosState,
    reportsState,
    selectedId,
    portfolio,
    report,
    newest,
    valuation,
    plannedAllocation
  } = dashboard;
  const { portfolios, listStatus, listError, selectPortfolio } = portfoliosState;
  const [range, setRange] = useState<DashboardRange>('1M');
  const analysis = report?.analysis;
  const points = useMemo(() => filterDashboardReturns(analysis?.portfolio_returns ?? [], range), [analysis, range]);
  const selected = portfolios.find((item) => item.id === selectedId);
  const firstName = (displayName || 'Investor').split(' ')[0];
  const holdingMode = portfolio ? portfolioHoldingMode(portfolio.holdings) : 'empty';
  const analyze = () => navigation.navigate('MoreTab', { screen: 'Analytics', params: { portfolioId: selectedId } });
  const openReport = () => {
    if (report) navigation.navigate('MoreTab', {
      screen: 'ReportDetail', params: { portfolioId: report.portfolio_id, reportId: report.id }
    });
  };

  if (listStatus === 'error' && !portfolios.length) {
    return (
      <SafeAreaView style={styles.safe}>
        <ScreenErrorState
          error={listError}
          resourceName="Portfolio list"
          fallbackMessage="Unable to load your dashboard."
          onRetry={() => void dashboard.refresh()}
        />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content} refreshControl={
        <RefreshControl refreshing={dashboard.refreshing} onRefresh={() => void dashboard.refresh()} tintColor={colors.primary} />
      }>
        <PageTitle eyebrow="AURA" title={`Welcome back, ${firstName}`} subtitle="Your portfolios and latest saved analysis." />

        {listStatus === 'error' ? (
          <InlineErrorCard
            error={listError}
            message={portfolioErrorMessage(listError)}
            stale
            onRetry={() => void dashboard.refresh()}
          />
        ) : null}

        {!portfolios.length ? (
          listStatus === 'idle' || listStatus === 'loading' ? (
            <Card style={styles.state}><Text style={styles.body}>Loading portfolios…</Text></Card>
          ) : listStatus === 'ready' ? (
            <Card style={styles.state}>
              <Text style={styles.heading}>No portfolios yet</Text>
              <Text style={styles.body}>Create a portfolio to start your risk dashboard.</Text>
              <Button title="Create Portfolio" onPress={() => navigation.navigate('Portfolio', { screen: 'CreatePortfolio' })} />
            </Card>
          ) : null
        ) : (
          <>
            <Card style={styles.state}>
              <Text style={styles.overline}>SELECTED PORTFOLIO</Text>
              <Text style={styles.heading}>{selected?.name}</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
                {portfolios.map((item) => (
                  <Pressable
                    accessibilityLabel={`${item.name} portfolio`}
                    accessibilityRole="radio"
                    accessibilityState={{ selected: item.id === selectedId }}
                    key={item.id}
                    onPress={() => selectPortfolio(item.id)}
                    style={[styles.chip, item.id === selectedId && styles.activeChip]}
                  >
                    <Text style={styles.chipText}>{item.name}</Text>
                  </Pressable>
                ))}
              </ScrollView>
              <Button title="Open Portfolio" variant="secondary" onPress={() => navigation.navigate('Portfolio', { screen: 'PortfolioDetail', params: { portfolioId: selectedId } })} />
            </Card>

            {dashboard.portfolioLoading ? <Text style={styles.notice}>Loading selected portfolio holdings…</Text> : null}
            {dashboard.portfolioError ? (
              <InlineErrorCard
                error={dashboard.portfolioError}
                message={portfolioErrorMessage(dashboard.portfolioError)}
                stale={Boolean(portfolio)}
                onRetry={dashboard.retryDetails}
                retryTitle="Retry holdings"
              />
            ) : null}

            {holdingMode === 'real' ? (
              <View style={styles.valuationControls}>
                <Text style={styles.overline}>CURRENT VALUE CURRENCY</Text>
                <View style={styles.currencyControl}>
                  {(['USD', 'THB'] as PortfolioCurrency[]).map((currency) => {
                    const active = dashboard.valuationCurrency === currency;
                    return (
                      <Pressable
                        accessibilityLabel={`${currency} valuation currency`}
                        accessibilityRole="radio"
                        accessibilityState={{ selected: active }}
                        key={currency}
                        onPress={() => dashboard.setValuationCurrency(currency)}
                        style={[styles.currencyOption, active && styles.activeCurrency]}
                      >
                        <Text style={[styles.currencyText, active && styles.activeCurrencyText]}>{currency}</Text>
                      </Pressable>
                    );
                  })}
                </View>
              </View>
            ) : null}

            {dashboard.valuationLoading ? <Text style={styles.notice}>{holdingMode === 'planned' ? 'Loading planned target allocation…' : 'Loading current portfolio value…'}</Text> : null}
            {dashboard.valuationError ? (
              <InlineErrorCard
                error={dashboard.valuationError}
                message={holdingMode === 'planned'
                  ? portfolioErrorMessage(dashboard.valuationError, 'Unable to load the planned target allocation.')
                  : portfolioValuationErrorMessage(dashboard.valuationError)}
                stale={Boolean(valuation)}
                onRetry={dashboard.retryDetails}
                retryTitle="Retry valuation"
              />
            ) : null}

            <View style={styles.kpiGrid}>
              <WebKpiCard
                icon="wallet-outline"
                label={holdingMode === 'planned' ? 'Proposed Investment' : 'Current Value'}
                value={holdingMode === 'planned' && plannedAllocation
                  ? formatPortfolioMoney(plannedAllocation.total_proposed_amount, plannedAllocation.plan_currency)
                  : valuation
                  ? formatPortfolioMoney(valuation.total_current_value, valuation.valuation_currency)
                  : 'N/A'}
                meta={holdingMode === 'planned' && plannedAllocation
                  ? 'Hypothetical plan · target weights from proposed amounts'
                  : valuation
                  ? `Prices as of ${valuation.newest_price_as_of}`
                  : holdingMode === 'legacy'
                    ? 'Legacy portfolios have saved weights only'
                    : 'Current valuation unavailable'}
                tone="blue"
              />
              <WebKpiCard icon="speedometer-outline" label="Risk Score" value={analysis?.risk_classification.risk_score == null ? 'N/A' : `${analysis.risk_classification.risk_score.toFixed(1)}/100`} meta={analysis?.risk_classification.risk_level ?? 'No verified report loaded'} tone={analysis ? riskTone(analysis.risk_classification.risk_level) : 'primary'} />
              <WebKpiCard icon="trending-up-outline" label="Annualized Return" value={dashboardPercent(analysis?.portfolio_metrics.annualized_return)} meta="Saved report period" />
              <WebKpiCard icon="trending-down-outline" label="Maximum Drawdown" value={dashboardPercent(analysis?.max_drawdown.max_drawdown)} meta="Saved report peak-to-trough" tone="danger" />
            </View>

            <SectionHeader title="Latest saved analysis" action="Analyze" onPress={analyze} />
            {reportsState.historyStatus === 'error' ? (
              <InlineErrorCard
                error={reportsState.historyError}
                message={reportErrorMessage(reportsState.historyError, 'Unable to verify the newest saved report.')}
                stale={Boolean(report)}
                onRetry={dashboard.retryDetails}
                retryTitle="Retry report history"
              />
            ) : reportsState.historyStatus === 'idle' || reportsState.historyStatus === 'loading' ? (
              <Card style={styles.state}><Text style={styles.body}>Loading report history…</Text></Card>
            ) : !newest ? (
              <Card style={styles.state}>
                <Text style={styles.heading}>No analysis yet</Text>
                <Text style={styles.body}>Analyze this portfolio to create a saved report.</Text>
                <Button title="Analyze Portfolio" onPress={analyze} />
              </Card>
            ) : (
              <>
                {reportsState.isRefreshing ? <Text style={styles.notice}>Refreshing report history; the displayed report is from the previous load.</Text> : null}
                {dashboard.reportLoading ? <Text style={styles.notice}>Loading newest saved report…</Text> : null}
                {dashboard.reportError ? (
                  <InlineErrorCard
                    error={dashboard.reportError}
                    message={reportErrorMessage(dashboard.reportError)}
                    stale={Boolean(report)}
                    onRetry={dashboard.retryDetails}
                    retryTitle="Retry report"
                  />
                ) : null}
                {report && analysis ? (
                  <>
                    <Card style={styles.state}>
                      <Text style={styles.heading}>{analysis.portfolio_name}</Text>
                      <Text style={styles.body}>Saved {formatReportTimestamp(report.created_at)}</Text>
                      <Text style={styles.body}>Requested: {analysis.start_date} → {analysis.end_date}</Text>
                      <Text style={styles.body}>Effective: {analysis.metadata.analysis_start} → {analysis.metadata.analysis_end}</Text>
                      <Text style={styles.body}>Metrics describe this saved report. Current holdings may have changed since it was created.</Text>
                      <Button title="Open saved report" variant="secondary" onPress={openReport} />
                    </Card>
                    <SectionHeader title="Portfolio periodic returns" />
                    <Card style={styles.state}>
                      <View style={styles.ranges}>
                        {ranges.map((item) => (
                          <Pressable
                            accessibilityLabel={`${item} chart range`}
                            accessibilityRole="radio"
                            accessibilityState={{ selected: range === item }}
                            key={item}
                            onPress={() => setRange(item)}
                            style={[styles.range, range === item && styles.activeChip]}
                          ><Text style={styles.chipText}>{item}</Text></Pressable>
                        ))}
                      </View>
                      <PortfolioReturnsChart points={points} />
                      <Text style={styles.body}>Chart window ends at the latest return observation. Filters change displayed points only; all metrics retain the saved report period.</Text>
                    </Card>
                    <SectionHeader title="Top Risk Drivers" action="View report" onPress={openReport} />
                    <Card>
                      {analysis.risk_drivers.entries.slice(0, 3).map((driver) => (
                        <View key={driver.symbol} style={styles.row}>
                          <Text style={styles.symbol}>{driver.rank}. {driver.symbol}</Text>
                          <View style={styles.contribution}>
                            <Text style={styles.weight}>{dashboardPercent(driver.percentage_volatility_contribution)}</Text>
                            <Text style={styles.body}>Volatility contribution</Text>
                          </View>
                        </View>
                      ))}
                    </Card>
                  </>
                ) : null}
              </>
            )}

            <SectionHeader title={holdingMode === 'planned' ? 'Planned Target Allocation' : 'Current Portfolio Allocation'} />
            <Card>
              {holdingMode === 'planned' && plannedAllocation ? plannedAllocation.holdings.map((holding) => (
                <View key={holding.symbol} style={styles.row}>
                  <Text style={styles.symbol}>{holding.symbol}</Text>
                  <Text style={styles.weight}>{dashboardPercent(Number(holding.target_allocation))}</Text>
                </View>
              )) : holdingMode === 'real' && valuation ? valuation.holdings.map((holding) => (
                <View key={holding.symbol} style={styles.row}>
                  <Text style={styles.symbol}>{holding.symbol}</Text>
                  <Text style={styles.weight}>{dashboardPercent(Number(holding.current_allocation))}</Text>
                </View>
              )) : holdingMode === 'legacy' && portfolio ? portfolio.holdings.map((holding) => (
                <View key={holding.symbol} style={styles.row}>
                  <Text style={styles.symbol}>{holding.symbol}</Text>
                  <Text style={styles.weight}>{dashboardPercent(holding.weight)}</Text>
                </View>
              )) : portfolio?.holdings.length ? (
                <Text style={styles.body}>Current allocation is unavailable until Aura can load market prices.</Text>
              ) : portfolio ? (
                <Text style={styles.body}>No holdings saved. Add holdings from Portfolio Detail.</Text>
              ) : <Text style={styles.body}>Allocation is unavailable until holdings load successfully.</Text>}
            </Card>
            <View style={styles.actions}>
              <Button title="Analyze Portfolio" onPress={analyze} />
              <Button title="Reports" variant="secondary" onPress={() => navigation.navigate('MoreTab', { screen: 'Reports' })} />
              <Button title="Simulations" variant="secondary" onPress={() => navigation.navigate('Simulate', { screen: 'Simulations' })} />
            </View>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 110 },
  state: { gap: spacing.md, marginTop: spacing.md },
  heading: { color: colors.text, fontSize: 17, fontWeight: '900' },
  overline: { color: colors.muted, fontSize: 10, fontWeight: '900' },
  body: { color: colors.textSecondary, fontSize: 12, lineHeight: 18 },
  error: { color: colors.danger, fontWeight: '800' },
  notice: { color: colors.textSecondary, fontSize: 12, marginTop: spacing.md },
  chips: { gap: spacing.sm },
  chip: { minHeight: 44, justifyContent: 'center', paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderRadius: 14, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surfaceAlt },
  activeChip: { borderColor: colors.primary, backgroundColor: colors.selectedBackground },
  chipText: { color: colors.text, fontSize: 11, fontWeight: '800' },
  kpiGrid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', gap: spacing.md, marginTop: spacing.md },
  ranges: { flexDirection: 'row', gap: spacing.xs },
  range: { flex: 1, minHeight: 44, alignItems: 'center', justifyContent: 'center', borderRadius: 10, borderWidth: 1, borderColor: colors.border },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: spacing.md, paddingVertical: spacing.md },
  symbol: { color: colors.text, fontWeight: '800', flex: 1 },
  weight: { color: colors.text, fontWeight: '900' },
  contribution: { alignItems: 'flex-end' },
  valuationControls: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: spacing.lg
  },
  currencyControl: { flexDirection: 'row', backgroundColor: colors.surfaceAlt, borderRadius: 12, padding: 3 },
  currencyOption: { minHeight: 44, justifyContent: 'center', paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderRadius: 9 },
  activeCurrency: { backgroundColor: colors.selectedBackground },
  currencyText: { color: colors.muted, fontSize: 11, fontWeight: '900' },
  activeCurrencyText: { color: colors.primary },
  actions: { gap: spacing.md, marginTop: spacing.xl }
});
