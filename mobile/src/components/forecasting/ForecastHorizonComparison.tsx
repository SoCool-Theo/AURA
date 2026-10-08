import React, { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { Card } from '../ui/Card';
import { usePortfolioPrivacy, usePrivateValue } from '../../privacy/PortfolioPrivacy';
import type { ForecastHorizon, OutlookResponse } from '../../types/forecasting';
import { comparisonPoints, forecastMoney, negativeMoney, forecastHorizons, forecastPercent, forecastReturn, forecastVolatility, forecastWarnings, type OutlookMetric } from '../../forecasting/forecastingUi';
import { forecastingStyles as styles } from '../../forecasting/forecastingStyles';
import { OutlookChart } from './OutlookChart';

export function ForecastQualityNotice({ results }: { results: OutlookResponse[] }) {
  if (!results.some(result => result.horizon_days !== 30)) return null;
  const warnings = forecastWarnings(results);
  return <View style={styles.quality}>
    <Text style={styles.warning}>Experimental Weekly V1 · not approved as reliable predictions. Each horizon uses separate models and calibration, not one daily forecast trajectory.</Text>
    {warnings.map(warning => <Text key={warning.key} style={styles.warning}>{warning.label}: {warning.message}</Text>)}
  </View>;
}

export function ForecastHorizonComparison({ results, loading, unavailable }: {
  results: OutlookResponse[]; loading: boolean; unavailable: ForecastHorizon[];
}) {
  const [metric, setMetric] = useState<OutlookMetric>('return');
  const [details, setDetails] = useState(false);
  const { hideValues } = usePortfolioPrivacy();
  const privateValue = usePrivateValue();
  const firstMoney = results.flatMap(item => 'portfolio_id' in item && item.monetary_projection ? [item.monetary_projection] : [])[0];
  const showAmounts = Boolean(firstMoney);
  const canChartMoney = showAmounts && !hideValues && results.every(item => 'portfolio_id' in item && item.monetary_projection?.currency === firstMoney.currency);
  const activeMetric = metric === 'change' && !canChartMoney ? 'return' : metric;
  const chartMetrics: OutlookMetric[] = canChartMoney ? ['return', 'change', 'volatility'] : ['return', 'volatility'];
  const points = comparisonPoints(results, activeMetric);
  return <Card style={styles.card}>
    <Text style={styles.heading}>Compare forecast horizons</Text>
    <Text style={styles.note}>Independent 7-, 14-, 21- and 30-calendar-day backend estimates.</Text>
    <Text style={styles.warning}>Weekly estimates are experimental and not approved as reliable predictions.</Text>
    <View style={styles.row}>{chartMetrics.map(value => <Pressable key={value} accessibilityRole="radio" accessibilityState={{ selected: activeMetric === value }} accessibilityLabel={value === 'return' ? 'Comparison Expected Return chart' : value === 'change' ? `Comparison Expected change (${firstMoney.currency}) chart` : 'Comparison Volatility chart'} onPress={() => setMetric(value)} style={[styles.option, activeMetric === value && styles.active]}><Text style={[styles.optionText, activeMetric === value && styles.activeText]}>{value === 'return' ? 'Expected Return' : value === 'change' ? `Expected change (${firstMoney.currency})` : 'Volatility'}</Text></Pressable>)}</View>
    {loading && <Text accessibilityLiveRegion="polite" style={styles.note}>Loading horizon comparisons…</Text>}
    {unavailable.length > 0 && <Text accessibilityLiveRegion="polite" style={styles.note}>Unavailable: {unavailable.map(day => `${day} days`).join(', ')}. Missing points are not estimated or replaced. Use Refresh to retry.</Text>}
    {points.length > 0 && <OutlookChart points={points} metric={activeMetric} />}
    <View accessibilityLabel="Forecast horizon comparison" style={{ gap: 8 }}>{forecastHorizons.map(day => {
      const result = results.find(item => item.horizon_days === day);
      const money = result && 'portfolio_id' in result ? result.monetary_projection : null;
      const status = result ? day === 30 ? 'V1 Preview' : 'Experimental Weekly V1' : unavailable.includes(day) ? 'Unavailable' : loading ? 'Loading…' : 'Not loaded';
      return <View key={day} style={styles.comparisonRow}>
        <Text style={styles.label}>{day} days · {status}</Text>
        <Text style={[styles.body, result && forecastReturn(result) < 0 && styles.negative]}>Expected return: {result ? forecastPercent(forecastReturn(result), true) : '—'}</Text>
        {showAmounts && <>
          <Text style={styles.body}>Baseline amount: {money ? privateValue(`${forecastMoney(money.baseline_amount, money.currency)} ${money.currency}`) : '—'}</Text>
          <Text style={[styles.body, money && negativeMoney(money.expected_change_amount) && styles.negative]}>Expected change: {money ? privateValue(forecastMoney(money.expected_change_amount, money.currency, true)) : '—'}</Text>
          <Text style={styles.body}>Estimated value: {money ? privateValue(forecastMoney(money.estimated_ending_value, money.currency)) : '—'}</Text>
        </>}
        <Text style={styles.body}>Forecast volatility: {result ? forecastPercent(forecastVolatility(result)) : '—'}</Text>
        <Text style={styles.note}>Market data as of: {result?.market_data_as_of ?? '—'}</Text>
      </View>;
    })}</View>
    {showAmounts && <Text style={styles.note}>Each horizon uses its own returned baseline amount. Planned amounts are hypothetical; THB assumes unchanged FX. Amounts are estimates, not guaranteed balances. Monetary lines do not connect different baselines or currencies.{hideValues && ' Amounts and monetary charts are hidden by your privacy setting.'}</Text>}
    {activeMetric === 'change' && points.length < results.length && <Text style={styles.note}>Some amounts cannot be plotted at the supported chart scale. Their full amounts remain in the cards.</Text>}
    <Text style={styles.note}>Amber points identify weekly estimates; teal identifies 30 days. Lines connect only adjacent available horizons with matching data dates. Review the dates before comparing.</Text>
    <ForecastQualityNotice results={results} />
    {results.length > 0 && <Pressable accessibilityRole="button" accessibilityLabel="Comparison model details and limitations" accessibilityState={{ expanded: details }} onPress={() => setDetails(value => !value)} style={styles.detailsButton}><Text style={styles.label}>Comparison model details and limitations</Text><Text style={styles.link}>{details ? '⌃' : '⌄'}</Text></Pressable>}
    {details && results.map(result => <View key={result.horizon_days} style={styles.comparisonRow}>
      <Text style={styles.label}>{result.horizon_days} days · {result.artifact_version}</Text>
      {('symbol' in result ? [result] : result.components).map(item => <View key={item.symbol}>
        <Text style={styles.note}>{item.symbol} · origin {item.forecast_origin_date}</Text>
        <Text style={styles.note}>Return model: {item.return_model_id}</Text>
        <Text style={styles.note}>Volatility model: {item.volatility_model_id}</Text>
      </View>)}
      {result.limitations.map(item => <Text key={item} style={styles.note}>• {item}</Text>)}
      {'portfolio_id' in result && result.monetary_projection && <><Text style={styles.label}>Monetary assumptions</Text>{result.monetary_projection.limitations.map(item => <Text key={item} style={styles.note}>• {item}</Text>)}</>}
    </View>)}
  </Card>;
}
