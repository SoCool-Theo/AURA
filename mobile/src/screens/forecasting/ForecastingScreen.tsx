import React, { useCallback, useRef, useState } from 'react';
import { useFocusEffect } from '@react-navigation/native';
import { Pressable, RefreshControl, ScrollView, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors } from '../../theme/theme';
import { useAuth } from '../../auth/useAuth';
import { portfoliosApi } from '../../api/portfoliosApi';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { PageTitle } from '../../components/ui/PageTitle';
import { InlineErrorCard } from '../../components/ui/ErrorState';
import { PortfolioSelector } from '../../components/simulations/PortfolioSelector';
import { ForecastingResults } from '../../components/forecasting/ForecastingResults';
import { ForecastHorizonComparison } from '../../components/forecasting/ForecastHorizonComparison';
import { useForecasting } from '../../forecasting/useForecasting';
import { forecastHorizons, forecastErrorMessage } from '../../forecasting/forecastingUi';
import { forecastingStyles as styles } from '../../forecasting/forecastingStyles';
import { supportedAssets } from '../../portfolio/supportedAssetSymbols';
import type { PortfolioSummaryResponse } from '../../types/portfolio';
import type { ForecastingParams } from '../../navigation/navigationTypes';
import type { ForecastHorizon } from '../../types/forecasting';

type Props = { route: { params?: ForecastingParams }; navigation: any };
export function ForecastingScreen(props: Props) {
  const { user } = useAuth();
  const params = props.route.params;
  return <AccountForecasting key={`${user?.id ?? ''}:${params?.scope ?? ''}:${params?.portfolioId ?? ''}:${params?.symbol ?? ''}`} {...props} />;
}
export function AccountForecasting({ route, navigation }: Props) {
  const { user, status } = useAuth();
  const account = status === 'authenticated' ? user?.id : undefined;
  const identity = useRef(account); identity.current = account;
  const [scope, setScope] = useState<'portfolio' | 'asset'>(route.params?.scope ?? 'portfolio');
  const [portfolioId, setPortfolioId] = useState(route.params?.portfolioId ?? '');
  const [symbol, setSymbol] = useState(route.params?.symbol?.trim().toUpperCase() || 'AAPL');
  const [query, setQuery] = useState('');
  const [horizon, setHorizon] = useState<ForecastHorizon>(30);
  const [compare, setCompare] = useState(false);
  const [list, setList] = useState<{ account?: string; items: PortfolioSummaryResponse[]; loading: boolean; error: unknown }>({ items: [], loading: true, error: null });
  const [revision, setRevision] = useState(0);
  const forecast = useForecasting(scope, scope === 'asset' ? symbol : portfolioId, horizon, compare);

  useFocusEffect(useCallback(() => {
    if (!account) return;
    const controller = new AbortController();
    const current = () => !controller.signal.aborted && identity.current === account;
    setList({ account, items: [], loading: true, error: null });
    const timeout = setTimeout(() => {
      if (current()) setList({ account, items: [], loading: false, error: new Error('Portfolio list timed out') });
      controller.abort();
    }, 20000);
    void portfoliosApi.list({ signal: controller.signal }).then(response => {
      if (!current()) return;
      setList({ account, items: response.portfolios, loading: false, error: null });
      setPortfolioId(value => value || response.portfolios[0]?.id || '');
    }).catch(error => {
      if (current()) setList({ account, items: [], loading: false, error });
    }).finally(() => clearTimeout(timeout));
    return () => { controller.abort(); clearTimeout(timeout); };
  }, [account, revision]));

  const portfolios = list.account === account ? list.items : [];
  const listError = list.account === account ? list.error : null;
  const listLoading = list.account !== account || list.loading;
  const matchingAssets = supportedAssets.filter(asset => `${asset.symbol} ${asset.name}`.toLowerCase().includes(query.trim().toLowerCase()));
  const openAsset = (assetSymbol: string) => navigation.push('Forecasting', { scope: 'asset', symbol: assetSymbol });
  const openPortfolio = () => navigation.getState().routeNames.includes('PortfolioDetail')
    ? navigation.navigate('PortfolioDetail', { portfolioId })
    : navigation.getParent()?.navigate('Portfolio', { screen: 'PortfolioDetail', params: { portfolioId } });
  const openAnalysis = () => navigation.navigate(navigation.getState().routeNames.includes('PortfolioAnalysis') ? 'PortfolioAnalysis' : 'Analytics', { portfolioId: portfolioId || undefined });

  return <SafeAreaView style={styles.safe} edges={['bottom']}>
    <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled" refreshControl={<RefreshControl refreshing={forecast.loading || forecast.comparisonLoading} onRefresh={forecast.refresh} tintColor={colors.primary} />}>
      <PageTitle eyebrow="MODEL-BASED FORECASTING" title="Forecast Outlook" subtitle="Model-based return and risk estimates, separate from historical analysis." right={<Pressable accessibilityRole="button" accessibilityLabel="Refresh Outlook" accessibilityState={{ disabled: forecast.loading || forecast.comparisonLoading || !(scope === 'asset' ? symbol : portfolioId) }} disabled={forecast.loading || forecast.comparisonLoading || !(scope === 'asset' ? symbol : portfolioId)} onPress={forecast.refresh} style={styles.refresh}><Text style={styles.link}>Refresh</Text></Pressable>} />
      <Text style={styles.badge}>{horizon === 30 ? 'V1 Preview' : 'Experimental Weekly V1'}</Text>
      <View style={styles.row}><Button title="Historical Analysis" variant="ghost" onPress={openAnalysis} />{scope === 'portfolio' && portfolioId ? <Button title="View Portfolio" variant="ghost" onPress={openPortfolio} /> : null}</View>
      <Card style={styles.card}>
        <View style={styles.row}>{(['portfolio', 'asset'] as const).map(value => <Pressable key={value} accessibilityRole="radio" accessibilityState={{ selected: scope === value }} accessibilityLabel={value === 'portfolio' ? 'Portfolio Outlook' : 'Asset Outlook'} onPress={() => setScope(value)} style={[styles.option, scope === value && styles.active]}><Text style={[styles.optionText, scope === value && styles.activeText]}>{value === 'portfolio' ? 'Portfolio Outlook' : 'Asset Outlook'}</Text></Pressable>)}</View>
        {scope === 'portfolio' ? <><Text style={styles.label}>Portfolio</Text>{listLoading ? <Text style={styles.note}>Loading portfolios…</Text> : null}<PortfolioSelector portfolios={portfolios} selectedId={portfolioId} onSelect={setPortfolioId} disabled={listLoading} />{portfolioId && !listLoading && !portfolios.some(item => item.id === portfolioId) ? <Text style={styles.note}>The requested portfolio is unavailable.</Text> : null}</> : <><Text style={styles.label}>Asset · {symbol}</Text><TextInput accessibilityLabel="Search forecast assets" value={query} onChangeText={setQuery} placeholder="Symbol or asset name" placeholderTextColor={colors.muted} autoCapitalize="characters" style={styles.search} /><ScrollView nestedScrollEnabled keyboardShouldPersistTaps="handled" style={styles.assetPicker}>{matchingAssets.map(asset => <Pressable key={asset.symbol} accessibilityRole="radio" accessibilityLabel={`Select ${asset.symbol}, ${asset.name}`} accessibilityState={{ selected: symbol === asset.symbol }} onPress={() => setSymbol(asset.symbol)} style={[styles.assetOption, symbol === asset.symbol && styles.active]}><Text style={styles.link}>{asset.symbol}</Text><Text style={styles.assetName}>{asset.name}</Text></Pressable>)}{!matchingAssets.length ? <Text style={styles.note}>No matching assets. Your selected asset is retained.</Text> : null}</ScrollView></>}
        <Text style={styles.label}>Forecast horizon</Text><View style={styles.row}>{forecastHorizons.map(days => <Pressable key={days} accessibilityRole="radio" accessibilityLabel={days + ' calendar days'} accessibilityState={{ selected: days === horizon }} onPress={() => setHorizon(days)} style={[styles.option, days === horizon && styles.active]}><Text style={[styles.optionText, days === horizon && styles.activeText]}>{days} days</Text>{days !== 30 ? <Text style={styles.tiny}>Experimental</Text> : null}</Pressable>)}</View>
        <Pressable accessibilityRole="checkbox" accessibilityLabel="Compare all forecast horizons" accessibilityState={{ checked: compare }} onPress={() => setCompare(value => !value)} style={[styles.option, compare && styles.active]}><Text style={[styles.optionText, compare && styles.activeText]}>{compare ? '✓ ' : ''}Compare all horizons</Text></Pressable>
        <Text style={styles.note}>Independent calendar-day estimates from frozen models. Weekly horizons are experimental, not approved as reliable predictions. Refresh reads saved market data; it does not retrain models.</Text>
      </Card>
      <Text style={styles.education}>Model-based estimates for educational use, not investment advice. Actual outcomes may differ. Prediction ranges are not guarantees or accuracy scores.</Text>
      {compare && Boolean(scope === 'asset' ? symbol : portfolioId) && <ForecastHorizonComparison key={`${scope}:${scope === 'asset' ? symbol : portfolioId}`} results={forecast.outlooks} loading={forecast.comparisonLoading} unavailable={forecast.unavailableHorizons} />}
      {scope === 'portfolio' && Boolean(listError) ? <InlineErrorCard error={listError} fallbackMessage="Unable to load your portfolios." onRetry={() => setRevision(value => value + 1)} /> : null}
      {Boolean(forecast.error) ? <InlineErrorCard error={forecast.error} message={forecastErrorMessage(forecast.error, scope)} resourceName="Outlook" onRetry={forecast.refresh} onBack={scope === 'portfolio' && portfolioId ? openPortfolio : undefined} backTitle="Review Portfolio" /> : null}
      {forecast.loading ? <Card><Text accessibilityLiveRegion="polite" style={styles.body}>Loading your {horizon}-day {scope} outlook…</Text><Text style={styles.note}>Using saved market data and the configured model artifacts.</Text></Card> : forecast.result ? <ForecastingResults key={`${scope}:${scope === 'asset' ? symbol : portfolioId}:${horizon}`} result={forecast.result} onAsset={openAsset} showChart={!compare} /> : scope === 'portfolio' && !portfolioId && !listLoading && !listError ? <Card style={styles.card}><Text style={styles.heading}>No portfolios yet</Text><Text style={styles.body}>Create a portfolio or explore an asset outlook without one.</Text><Button title="Explore Assets" onPress={() => setScope('asset')} /><Button title="Create Portfolio" variant="secondary" onPress={() => navigation.getParent()?.navigate('Portfolio', { screen: 'CreatePortfolio' })} /></Card> : null}
    </ScrollView>
  </SafeAreaView>;
}
