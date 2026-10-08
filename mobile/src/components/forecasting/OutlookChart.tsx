import React from 'react';
import { Text, View } from 'react-native';
import Svg, { Circle, G, Line, Polyline, Text as SvgText } from 'react-native-svg';
import { colors } from '../../theme/theme';
import { forecastHorizons, forecastPercent, type OutlookMetric, type OutlookPoint } from '../../forecasting/forecastingUi';
import { forecastingStyles as styles } from '../../forecasting/forecastingStyles';

export function OutlookChart({ points, metric }: { points: OutlookPoint[]; metric: OutlookMetric }) {
  const ordered = [...points].sort((a, b) => a.horizonDays - b.horizonDays);
  // Only visual guides between adjacent, same-date estimates. Never bridge gaps.
  const segments = ordered.flatMap((point, index) => {
    const next = ordered[index + 1];
    return next && forecastHorizons.indexOf(next.horizonDays as 7 | 14 | 21 | 30)
      === forecastHorizons.indexOf(point.horizonDays as 7 | 14 | 21 | 30) + 1
      && point.dataDate && point.dataDate === next.dataDate ? [[point, next]] : [];
  });
  const values = [0, ...ordered.flatMap(point => [point.estimate, ...(point.interval ? [point.interval.lower, point.interval.upper] : [])])];
  const minimum = Math.min(...values), maximum = Math.max(...values);
  const padding = Math.max((maximum - minimum) * 0.12, 0.001);
  const low = metric === 'volatility' ? 0 : minimum - padding, high = maximum + padding;
  const x = (day: number) => 68 + ((day - 7) / 23) * 267;
  const y = (value: number) => 170 - ((value - low) / (high - low)) * 145;
  const label = metric === 'return' ? 'Expected return (%)' : 'Forecast volatility (%) · non-annualized';
  const description = ordered.map(point => point.horizonDays + ' days: ' + forecastPercent(point.estimate)
    + (point.interval ? ', nominal 80% range ' + forecastPercent(point.interval.lower) + ' to ' + forecastPercent(point.interval.upper) : '')).join('. ');
  return <View style={{ gap: 9 }}>
    <Text style={styles.label}>{label}</Text>
    <View accessible accessibilityRole="image" accessibilityLabel={label + '. ' + description}>
      <Svg width="100%" height={220} viewBox="0 0 375 220">
        {[0, 1, 2, 3, 4].map(tick => {
          const value = low + ((high - low) * tick / 4);
          return <G key={tick}><Line x1={68} x2={348} y1={y(value)} y2={y(value)} stroke={colors.borderSoft} /><SvgText x={60} y={y(value) + 4} textAnchor="end" fontSize={10} fill={colors.muted}>{forecastPercent(value)}</SvgText></G>;
        })}
        <Line x1={68} x2={348} y1={y(0)} y2={y(0)} stroke={colors.muted} strokeDasharray="4 5" opacity={0.5} />
        {forecastHorizons.map(day => <G key={day}><Line x1={x(day)} x2={x(day)} y1={25} y2={170} stroke={colors.borderSoft} /><SvgText x={x(day)} y={191} textAnchor="middle" fontSize={10} fill={colors.muted}>{day} days</SvgText></G>)}
        {segments.map(segment => <Polyline key={segment[0].horizonDays} points={segment.map(point => `${x(point.horizonDays)},${y(point.estimate)}`).join(' ')} fill="none" stroke={colors.primary} strokeWidth={2} strokeDasharray="7 5" />)}
        {ordered.map(point => <G key={point.horizonDays}>
          {point.interval && <G><Line x1={x(point.horizonDays)} x2={x(point.horizonDays)} y1={y(point.interval.lower)} y2={y(point.interval.upper)} stroke={colors.primarySoft} strokeWidth={2} /><Line x1={x(point.horizonDays) - 6} x2={x(point.horizonDays) + 6} y1={y(point.interval.lower)} y2={y(point.interval.lower)} stroke={colors.primarySoft} strokeWidth={2} /><Line x1={x(point.horizonDays) - 6} x2={x(point.horizonDays) + 6} y1={y(point.interval.upper)} y2={y(point.interval.upper)} stroke={colors.primarySoft} strokeWidth={2} /></G>}
          <Circle cx={x(point.horizonDays)} cy={y(point.estimate)} r={5} fill={point.horizonDays === 30 ? colors.primary : colors.warning} stroke={colors.surface} strokeWidth={2} />
          <SvgText x={x(point.horizonDays)} y={y(point.estimate) - 9} textAnchor={point.horizonDays === 7 ? 'start' : point.horizonDays === 30 ? 'end' : 'middle'} fontSize={11} fontWeight="bold" fill={colors.text}>{forecastPercent(point.estimate, metric === 'return')}</SvgText>
        </G>)}
        <SvgText x={200} y={214} textAnchor="middle" fontSize={9} fill={colors.muted}>Calendar days ahead from each forecast origin</SvgText>
      </Svg>
    </View>
    <Text style={styles.note}>Each marker is an independent calendar-day estimate, not a daily price path. Weekly estimates are experimental. {ordered.some(point => point.interval) ? 'Bars show nominal 80% asset prediction ranges.' : 'No calibrated portfolio prediction range is provided.'} Dashed lines are visual guides only; missing horizons or different data dates break the line.</Text>
  </View>;
}
