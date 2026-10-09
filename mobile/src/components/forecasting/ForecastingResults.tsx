import React, { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { OutlookChart } from './OutlookChart';
import { ForecastQualityNotice } from './ForecastHorizonComparison';
import { usePortfolioPrivacy, usePrivateValue } from '../../privacy/PortfolioPrivacy';
import type { OutlookResponse } from '../../types/forecasting';
import { forecastBaselineLabel, forecastMoney, negativeMoney, forecastPercent, forecastPoints, forecastReturn, forecastVolatility, type OutlookMetric } from '../../forecasting/forecastingUi';
import { forecastingStyles as styles } from '../../forecasting/forecastingStyles';

function DataRow({ label, value, negative = false }: { label: string; value: string; negative?: boolean }) {
  return <View style={styles.dataRow}><Text style={styles.dataLabel}>{label}</Text><Text style={[styles.dataValue, negative && styles.negative]}>{value}</Text></View>;
}
export function ForecastingResults({ result, onAsset, showChart = true }: { result: OutlookResponse; onAsset: (symbol: string) => void; showChart?: boolean }) {
  const [metric, setMetric] = useState<OutlookMetric>('return');
  const [details, setDetails] = useState(false);
  const asset = 'symbol' in result;
  const money = asset ? null : result.monetary_projection;
  const { hideValues } = usePortfolioPrivacy();
  const privateValue = usePrivateValue();
  const activeMetric = metric === 'change' && (!money || hideValues) ? 'return' : metric;
  const chartMetrics: OutlookMetric[] = money && !hideValues ? ['return', 'change', 'volatility'] : ['return', 'volatility'];
  const points = forecastPoints(result, activeMetric);
  const components = asset ? [] : result.components;
  const expectedReturn = forecastReturn(result);
  const volatility = forecastVolatility(result);
  // Geometry only. Never recompute or clamp backend financial contributions.
  const negative = Math.min(0, ...components.map(item => item.forecast_volatility_contribution_share));
  const positive = Math.max(0, ...components.map(item => item.forecast_volatility_contribution_share));
  const span = positive - negative || 1, zero = -negative / span * 100;
  return <View style={{ gap: 14 }}>
    <ForecastQualityNotice results={[result]} />
    <Card style={styles.card}>
      <Text style={styles.title}>{asset ? result.symbol : result.portfolio_name}</Text>
      <Text style={styles.body}>{asset ? 'Standalone asset estimate · ownership is not required' : forecastBaselineLabel(result.baseline_kind)}</Text>
      <DataRow label="Market data as of" value={result.market_data_as_of} />
      <DataRow label="Model version" value={result.artifact_version} />
      {asset ? <><DataRow label="Forecast origin" value={result.forecast_origin_date} /><DataRow label="Data age" value={result.market_data_age_days + ' calendar days'} /></> : <><DataRow label="Correlation as of" value={result.correlation_as_of_date} /><DataRow label="Common observations" value={String(result.correlation_observation_count)} /></>}
    </Card>
    <Card style={styles.metric}>
      <Text style={styles.label}>Expected {result.horizon_days}-Day Return</Text>
      <Text style={[styles.number, expectedReturn < 0 && styles.negative]}>{forecastPercent(expectedReturn, true)}</Text>
      <Text style={styles.note}>Model estimate, not a guaranteed outcome.</Text>
      {asset && <Text style={styles.body}>80% prediction range: {forecastPercent(result.return_prediction_interval.lower)} to {forecastPercent(result.return_prediction_interval.upper)}</Text>}
    </Card>
    <Card style={styles.metric}>
      <Text style={styles.label}>Forecast {result.horizon_days}-Day Volatility</Text>
      <Text style={styles.number}>{forecastPercent(volatility)}</Text>
      <Text style={styles.note}>Non-annualized · not comparable directly with annualized historical volatility.</Text>
      {asset && <Text style={styles.body}>80% prediction range: {forecastPercent(result.volatility_prediction_interval.lower)} to {forecastPercent(result.volatility_prediction_interval.upper)}</Text>}
    </Card>
    {money && <Card style={styles.card}>
      <Text style={styles.heading}>Portfolio amount outlook</Text>
      <Text style={styles.note}>{money.hypothetical ? 'Hypothetical planned investment' : 'Current portfolio market value'} · {money.currency} · backend-calculated estimates</Text>
      <View style={styles.moneyMetric}><Text style={styles.label}>{money.hypothetical ? 'Planned investment' : 'Current portfolio value'}</Text><Text style={styles.moneyNumber}>{privateValue(forecastMoney(money.baseline_amount, money.currency))}</Text></View>
      <View style={styles.moneyMetric}><Text style={styles.label}>Expected {result.horizon_days}-day change</Text><Text style={[styles.moneyNumber, negativeMoney(money.expected_change_amount) && styles.negative]}>{privateValue(forecastMoney(money.expected_change_amount, money.currency, true))}</Text></View>
      <View style={styles.moneyMetric}><Text style={styles.label}>Estimated {result.horizon_days}-day value</Text><Text style={styles.moneyNumber}>{privateValue(forecastMoney(money.estimated_ending_value, money.currency))}</Text></View>
      <Text style={styles.note}>{money.hypothetical ? 'Based on the investment amounts you entered, not assets you currently own.' : `Based on saved prices × owned shares, not purchase cost. Valuation requested ${money.valuation_requested_date}; prices from ${money.oldest_price_as_of} to ${money.newest_price_as_of}.`} {money.assumes_unchanged_fx && 'THB estimates assume unchanged exchange rates; this is not an FX forecast.'} Amounts are estimates, not guaranteed balances. Fees, taxes and cash flows are excluded.</Text>
      {hideValues && <Text style={styles.note}>Amounts and monetary charts are hidden by your privacy setting.</Text>}
    </Card>}
    {!asset && result.baseline_kind === 'legacy' && <Text style={styles.note}>Legacy saved weights do not establish an investment amount. This Outlook remains percentage-only.</Text>}
    {showChart && <Card style={styles.card}>
      <Text style={styles.heading}>Outlook by horizon</Text>
      <View style={styles.row}>{chartMetrics.map(value => <Pressable key={value} accessibilityRole="radio" accessibilityState={{ selected: activeMetric === value }} accessibilityLabel={value === 'return' ? 'Expected Return chart' : value === 'change' ? `Expected change (${money?.currency}) chart` : 'Volatility chart'} onPress={() => setMetric(value)} style={[styles.option, activeMetric === value && styles.active]}><Text style={[styles.optionText, activeMetric === value && styles.activeText]}>{value === 'return' ? 'Expected Return' : value === 'change' ? `Expected change (${money?.currency})` : 'Volatility'}</Text></Pressable>)}</View>
      {points.length ? <OutlookChart points={points} metric={activeMetric} /> : <Text style={styles.note}>This amount cannot be plotted at the supported chart scale. Review the full amount above.</Text>}
    </Card>}
    {!asset && <>
      <Card style={styles.card}><Text style={styles.heading}>Forecast Risk Contributors</Text><Text style={styles.note}>Share of forecast portfolio volatility. Negative contributions can offset other components; correlations may change.</Text>
        {components.map(item => {
          const share = item.forecast_volatility_contribution_share;
          return <View key={item.symbol} style={styles.driver}><Pressable accessibilityRole="button" accessibilityLabel={`View ${item.symbol} outlook`} onPress={() => onAsset(item.symbol)} style={styles.driverTop}><Text style={styles.link}>{item.symbol} ›</Text><Text style={styles.label}>{forecastPercent(share, true)}</Text></Pressable><View style={styles.track}><View style={[styles.origin, { left: `${zero}%` }]} /><View style={[styles.bar, share < 0 && styles.negativeBar, { left: `${share < 0 ? (share - negative) / span * 100 : zero}%`, width: `${Math.abs(share) / span * 100}%` }]} /></View></View>;
        })}
      </Card>
      <Text style={styles.heading}>Asset breakdown</Text><Text style={styles.note}>Backend-resolved allocation and individual outlooks. Component origins can differ; the portfolio data date is the oldest component.</Text>
      {money && <Text style={styles.note}>Each amount uses that holding’s own baseline and forecast return, not the overall portfolio return. Asset drill-down opens the standalone 30-day outlook without your holding amount.</Text>}
      {components.map(item => {
        const holding = item.monetary_projection;
        return <Card style={styles.card} key={item.symbol}>
          <Text style={styles.heading}>{item.symbol}</Text>
          <DataRow label="Allocation" value={forecastPercent(item.current_weight)} />
          {holding && <DataRow label={`${holding.hypothetical ? 'Planned amount' : 'Current value'} (${holding.currency})`} value={privateValue(forecastMoney(holding.baseline_amount, holding.currency))} />}
          <DataRow label={`${item.horizon_days}-day expected return`} value={forecastPercent(forecastReturn(item), true)} />
          {holding && <><DataRow label={`${item.horizon_days}-day expected change (${holding.currency})`} value={privateValue(forecastMoney(holding.expected_change_amount, holding.currency, true))} negative={negativeMoney(holding.expected_change_amount)} /><DataRow label={`Estimated value (${holding.currency})`} value={privateValue(forecastMoney(holding.estimated_ending_value, holding.currency))} /></>}
          <DataRow label={`${item.horizon_days}-day volatility`} value={forecastPercent(forecastVolatility(item))} />
          <DataRow label="Volatility contribution" value={forecastPercent(item.forecast_volatility_contribution, true)} />
          <DataRow label="Origin" value={item.forecast_origin_date} />
          {holding?.oldest_price_as_of && <DataRow label="Holding price as of" value={holding.oldest_price_as_of} />}
          <Button title="View Outlook" accessibilityLabel={`View ${item.symbol} asset outlook`} variant="secondary" onPress={() => onAsset(item.symbol)} />
        </Card>;
      })}
    </>}
    <Card style={styles.card}>
      <Pressable accessibilityRole="button" accessibilityLabel="Model details and limitations" accessibilityState={{ expanded: details }} onPress={() => setDetails(value => !value)} style={styles.detailsButton}><Text style={styles.label}>Model details and limitations</Text><Text style={styles.link}>{details ? '⌃' : '⌄'}</Text></Pressable>
      {details && <>{asset ? <><DataRow label="Return model" value={result.return_model_id} /><DataRow label="Volatility model" value={result.volatility_model_id} /></> : components.map(item => <View key={item.symbol}><Text style={styles.label}>{item.symbol}</Text><DataRow label="Return model" value={item.return_model_id} /><DataRow label="Volatility model" value={item.volatility_model_id} /></View>)}{result.limitations.map(item => <Text key={item} style={styles.note}>• {item}</Text>)}{money && <><Text style={styles.label}>Monetary assumptions</Text>{money.limitations.map(item => <Text key={item} style={styles.note}>• {item}</Text>)}</>}</>}
    </Card>
  </View>;
}
