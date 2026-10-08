import React, { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { OutlookChart } from './OutlookChart';
import type { OutlookResponse } from '../../types/forecasting';
import { forecastBaselineLabel, forecastPercent, forecastPoints, type OutlookMetric } from '../../forecasting/forecastingUi';
import { forecastingStyles as styles } from '../../forecasting/forecastingStyles';

function DataRow({ label, value }: { label: string; value: string }) {
  return <View style={styles.dataRow}><Text style={styles.dataLabel}>{label}</Text><Text style={styles.dataValue}>{value}</Text></View>;
}
export function ForecastingResults({ result, onAsset }: { result: OutlookResponse; onAsset: (symbol: string) => void }) {
  const [metric, setMetric] = useState<OutlookMetric>('return');
  const [details, setDetails] = useState(false);
  const asset = 'symbol' in result;
  const components = asset ? [] : result.components;
  // Geometry only. Never recompute or clamp backend financial contributions.
  const negative = Math.min(0, ...components.map(item => item.forecast_volatility_contribution_share));
  const positive = Math.max(0, ...components.map(item => item.forecast_volatility_contribution_share));
  const span = positive - negative || 1, zero = -negative / span * 100;
  return <View style={{ gap: 14 }}>
    <Card style={styles.card}>
      <Text style={styles.title}>{asset ? result.symbol : result.portfolio_name}</Text>
      <Text style={styles.body}>{asset ? 'Standalone asset estimate · ownership is not required' : forecastBaselineLabel(result.baseline_kind)}</Text>
      <DataRow label="Market data as of" value={result.market_data_as_of} />
      <DataRow label="Model version" value={result.artifact_version} />
      {asset ? <><DataRow label="Forecast origin" value={result.forecast_origin_date} /><DataRow label="Data age" value={result.market_data_age_days + ' calendar days'} /></> : <><DataRow label="Correlation as of" value={result.correlation_as_of_date} /><DataRow label="Common observations" value={String(result.correlation_observation_count)} /></>}
    </Card>
    <Card style={styles.metric}>
      <Text style={styles.label}>Expected 30-Day Return</Text>
      <Text style={[styles.number, result.expected_return_30d < 0 && styles.negative]}>{forecastPercent(result.expected_return_30d, true)}</Text>
      <Text style={styles.note}>Model estimate, not a guaranteed outcome.</Text>
      {asset && <Text style={styles.body}>80% prediction range: {forecastPercent(result.return_prediction_interval.lower)} to {forecastPercent(result.return_prediction_interval.upper)}</Text>}
    </Card>
    <Card style={styles.metric}>
      <Text style={styles.label}>Forecast 30-Day Volatility</Text>
      <Text style={styles.number}>{forecastPercent(result.forecast_realized_volatility_30d)}</Text>
      <Text style={styles.note}>Non-annualized · not comparable directly with annualized historical volatility.</Text>
      {asset && <Text style={styles.body}>80% prediction range: {forecastPercent(result.volatility_prediction_interval.lower)} to {forecastPercent(result.volatility_prediction_interval.upper)}</Text>}
    </Card>
    <Card style={styles.card}>
      <Text style={styles.heading}>Outlook by horizon</Text>
      <View style={styles.row}>{(['return', 'volatility'] as OutlookMetric[]).map(value => <Pressable key={value} accessibilityRole="radio" accessibilityState={{ selected: metric === value }} accessibilityLabel={value === 'return' ? 'Expected Return chart' : 'Volatility chart'} onPress={() => setMetric(value)} style={[styles.option, metric === value && styles.active]}><Text style={[styles.optionText, metric === value && styles.activeText]}>{value === 'return' ? 'Expected Return' : 'Volatility'}</Text></Pressable>)}</View>
      <OutlookChart points={forecastPoints(result, metric)} metric={metric} />
    </Card>
    {!asset && <>
      <Card style={styles.card}><Text style={styles.heading}>Forecast Risk Contributors</Text><Text style={styles.note}>Share of forecast portfolio volatility. Negative contributions can offset other components; correlations may change.</Text>
        {components.map(item => {
          const share = item.forecast_volatility_contribution_share;
          return <View key={item.symbol} style={styles.driver}><Pressable accessibilityRole="button" accessibilityLabel={`View ${item.symbol} outlook`} onPress={() => onAsset(item.symbol)} style={styles.driverTop}><Text style={styles.link}>{item.symbol} ›</Text><Text style={styles.label}>{forecastPercent(share, true)}</Text></Pressable><View style={styles.track}><View style={[styles.origin, { left: `${zero}%` }]} /><View style={[styles.bar, share < 0 && styles.negativeBar, { left: `${share < 0 ? (share - negative) / span * 100 : zero}%`, width: `${Math.abs(share) / span * 100}%` }]} /></View></View>;
        })}
      </Card>
      <Text style={styles.heading}>Asset breakdown</Text><Text style={styles.note}>Backend-resolved allocation and individual outlooks. Component origins can differ; the portfolio data date is the oldest component.</Text>
      {components.map(item => <Card style={styles.card} key={item.symbol}><Text style={styles.heading}>{item.symbol}</Text><DataRow label="Allocation" value={forecastPercent(item.current_weight)} /><DataRow label="30-day expected return" value={forecastPercent(item.expected_return_30d, true)} /><DataRow label="30-day volatility" value={forecastPercent(item.forecast_realized_volatility_30d)} /><DataRow label="Volatility contribution" value={forecastPercent(item.forecast_volatility_contribution, true)} /><DataRow label="Origin" value={item.forecast_origin_date} /><Button title="View Outlook" accessibilityLabel={`View ${item.symbol} asset outlook`} variant="secondary" onPress={() => onAsset(item.symbol)} /></Card>)}
    </>}
    <Card style={styles.card}>
      <Pressable accessibilityRole="button" accessibilityLabel="Model details and limitations" accessibilityState={{ expanded: details }} onPress={() => setDetails(value => !value)} style={styles.detailsButton}><Text style={styles.label}>Model details and limitations</Text><Text style={styles.link}>{details ? '⌃' : '⌄'}</Text></Pressable>
      {details && <>{asset ? <><DataRow label="Return model" value={result.return_model_id} /><DataRow label="Volatility model" value={result.volatility_model_id} /></> : components.map(item => <View key={item.symbol}><Text style={styles.label}>{item.symbol}</Text><DataRow label="Return model" value={item.return_model_id} /><DataRow label="Volatility model" value={item.volatility_model_id} /></View>)}{result.limitations.map(item => <Text key={item} style={styles.note}>• {item}</Text>)}</>}
    </Card>
  </View>;
}
