import React, { useMemo, useState } from 'react';
import { Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { PageTitle } from '../../components/ui/PageTitle';
import { SectionHeader } from '../../components/ui/SectionHeader';
import { WebKpiCard } from '../../components/ui/WebKpiCard';
import { PortfolioReturnsChart } from '../../components/charts/PortfolioReturnsChart';
import { useDashboard } from '../../dashboard/useDashboard';
import { dashboardPercent, filterDashboardReturns, type DashboardRange } from '../../dashboard/dashboardPresentation';
import { usePreferences } from '../../preferences/usePreferences';
import { portfolioErrorMessage } from '../../portfolio/portfolioErrors';
import { reportErrorMessage } from '../../report/reportErrors';
import { formatReportTimestamp, riskTone } from '../../report/reportFormatting';
import { colors, spacing } from '../../theme/theme';

const ranges: DashboardRange[] = ['1M', '3M', '6M', '1Y', 'ALL'];

export function DashboardScreen({ navigation }: { navigation: any }) {
  const { displayName } = usePreferences();
  const dashboard = useDashboard();
  const { portfoliosState, reportsState, selectedId, portfolio, report, newest } = dashboard;
  const { portfolios, listStatus, listError, selectPortfolio } = portfoliosState;
  const [range, setRange] = useState<DashboardRange>('1M');
  const analysis = report?.analysis;
  const points = useMemo(() => filterDashboardReturns(analysis?.portfolio_returns ?? [], range), [analysis, range]);
  const selected = portfolios.find((item) => item.id === selectedId);
  const firstName = (displayName || 'Investor').split(' ')[0];
  const analyze = () => navigation.navigate('MoreTab', { screen: 'Analytics', params: { portfolioId: selectedId } });
  const openReport = () => {
    if (report) navigation.navigate('MoreTab', {
      screen: 'ReportDetail', params: { portfolioId: report.portfolio_id, reportId: report.id }
    });
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content} refreshControl={
        <RefreshControl refreshing={dashboard.refreshing} onRefresh={() => void dashboard.refresh()} tintColor={colors.primary} />
      }>
        <PageTitle eyebrow="AURA" title={`Welcome back, ${firstName}`} subtitle="Your portfolios and latest saved analysis." />

        {listStatus === 'error' ? (
          <Card style={styles.state}>
            <Text style={styles.error}>Could not refresh portfolios</Text>
            <Text style={styles.body}>{portfolioErrorMessage(listError)}</Text>
            {portfolios.length ? <Text style={styles.body}>Showing the previously loaded portfolio list.</Text> : null}
            <Button title="Retry" disabled={dashboard.refreshing} onPress={() => void dashboard.refresh()} />
          </Card>
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
                  <Pressable key={item.id} onPress={() => selectPortfolio(item.id)} style={[styles.chip, item.id === selectedId && styles.activeChip]}>
                    <Text style={styles.chipText}>{item.name}</Text>
                  </Pressable>
                ))}
              </ScrollView>
              <Button title="Open Portfolio" variant="secondary" onPress={() => navigation.navigate('Portfolio', { screen: 'PortfolioDetail', params: { portfolioId: selectedId } })} />
            </Card>

            {dashboard.portfolioLoading ? <Text style={styles.notice}>Loading selected portfolio holdings…</Text> : null}
            {dashboard.portfolioError ? (
              <Card style={styles.state}>
                <Text style={styles.error}>Holdings unavailable or could not refresh</Text>
                <Text style={styles.body}>{portfolioErrorMessage(dashboard.portfolioError)}</Text>
                {portfolio ? <Text style={styles.body}>Showing previously loaded holdings; they may be out of date.</Text> : null}
                <Button title="Retry holdings" disabled={dashboard.refreshing} onPress={dashboard.retryDetails} />
              </Card>
            ) : null}

            <View style={styles.kpiGrid}>
              <WebKpiCard icon="layers-outline" label="Holdings Count" value={portfolio ? String(portfolio.holdings.length) : 'N/A'} meta="Saved portfolio holdings" tone="blue" />
              <WebKpiCard icon="speedometer-outline" label="Risk Score" value={analysis?.risk_classification.risk_score == null ? 'N/A' : `${analysis.risk_classification.risk_score.toFixed(1)}/100`} meta={analysis?.risk_classification.risk_level ?? 'No verified report loaded'} tone={analysis ? riskTone(analysis.risk_classification.risk_level) : 'primary'} />
              <WebKpiCard icon="trending-up-outline" label="Annualized Return" value={dashboardPercent(analysis?.portfolio_metrics.annualized_return)} meta="Saved report period" />
              <WebKpiCard icon="trending-down-outline" label="Maximum Drawdown" value={dashboardPercent(analysis?.max_drawdown.max_drawdown)} meta="Saved report peak-to-trough" tone="danger" />
            </View>

            <SectionHeader title="Latest saved analysis" action="Analyze" onPress={analyze} />
            {reportsState.historyStatus === 'error' ? (
              <Card style={styles.state}>
                <Text style={styles.error}>Report history unavailable</Text>
                <Text style={styles.body}>{reportErrorMessage(reportsState.historyError, 'Unable to verify the newest saved report.')}</Text>
                <Text style={styles.body}>Analytics are unavailable until history can be verified. Loaded holdings remain available below.</Text>
                <Button title="Retry report history" disabled={dashboard.refreshing} onPress={dashboard.retryDetails} />
              </Card>
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
                  <Card style={styles.state}>
                    <Text style={styles.error}>Could not load the newest report</Text>
                    <Text style={styles.body}>{reportErrorMessage(dashboard.reportError)}</Text>
                    {report ? <Text style={styles.body}>Showing the previously loaded immutable report.</Text> : null}
                    <Button title="Retry report" disabled={dashboard.refreshing} onPress={dashboard.retryDetails} />
                  </Card>
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
                          <Pressable key={item} onPress={() => setRange(item)} style={[styles.range, range === item && styles.activeChip]}><Text style={styles.chipText}>{item}</Text></Pressable>
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

            <SectionHeader title="Current Portfolio Allocation" />
            <Card>
              {portfolio ? portfolio.holdings.length ? portfolio.holdings.map((holding) => (
                <View key={holding.symbol} style={styles.row}>
                  <Text style={styles.symbol}>{holding.symbol}</Text>
                  <Text style={styles.weight}>{dashboardPercent(holding.weight)}</Text>
                </View>
              )) : <Text style={styles.body}>No holdings saved. Add holdings from Portfolio Detail.</Text>
                : <Text style={styles.body}>Allocation is unavailable until holdings load successfully.</Text>}
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
  chip: { paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderRadius: 14, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surfaceAlt },
  activeChip: { borderColor: colors.primary, backgroundColor: colors.selectedBackground },
  chipText: { color: colors.text, fontSize: 11, fontWeight: '800' },
  kpiGrid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', gap: spacing.md, marginTop: spacing.md },
  ranges: { flexDirection: 'row', gap: spacing.xs },
  range: { flex: 1, minHeight: 36, alignItems: 'center', justifyContent: 'center', borderRadius: 10, borderWidth: 1, borderColor: colors.border },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: spacing.md, paddingVertical: spacing.md },
  symbol: { color: colors.text, fontWeight: '800', flex: 1 },
  weight: { color: colors.text, fontWeight: '900' },
  contribution: { alignItems: 'flex-end' },
  actions: { gap: spacing.md, marginTop: spacing.xl }
});
