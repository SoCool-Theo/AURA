import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import Svg, { Line, Polyline, Text as SvgText } from 'react-native-svg';

import type { HistoricalScenarioTrajectoryPoint } from '../../types/simulation';
import { colors, spacing } from '../../theme/theme';

const WIDTH = 340;
const HEIGHT = 180;
const LEFT = 48;
const RIGHT = 328;
const TOP = 18;
const BOTTOM = 142;

export function SimulationTrajectoryChart({
  series
}: {
  series: Array<{
    label: string;
    color: string;
    points: HistoricalScenarioTrajectoryPoint[];
  }>;
}) {
  const [selectedSeries, setSelectedSeries] = useState('all');
  const visibleSeries = selectedSeries === 'all'
    ? series
    : series.filter((item) => item.label === selectedSeries);
  const values = visibleSeries.flatMap((item) => item.points.map((point) => point.normalized_value));
  if (!values.length) return <Text style={styles.empty}>No trajectory observations returned.</Text>;

  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const range = maximum - minimum || 1;
  const selectedPoints = selectedSeries === 'all' ? null : visibleSeries[0]?.points;

  function coordinates(points: HistoricalScenarioTrajectoryPoint[]): string {
    return points.map((point, index) => {
      const x = LEFT + (index / Math.max(points.length - 1, 1)) * (RIGHT - LEFT);
      const y = TOP + ((maximum - point.normalized_value) / range) * (BOTTOM - TOP);
      return `${x},${y}`;
    }).join(' ');
  }

  return (
    <View>
      {series.length > 1 ? (
        <View style={styles.controls} accessibilityRole="radiogroup" accessibilityLabel="Choose trajectory lines">
          {['all', ...series.map((item) => item.label)].map((value) => {
            const selected = selectedSeries === value;
            return (
              <Pressable
                key={value}
                accessibilityRole="radio"
                accessibilityState={{ selected }}
                onPress={() => setSelectedSeries(value)}
                style={[styles.control, selected && styles.controlSelected]}
              >
                <Text style={[styles.controlText, selected && styles.controlTextSelected]}>
                  {value === 'all' ? 'All lines' : value}
                </Text>
              </Pressable>
            );
          })}
        </View>
      ) : null}
      <Svg width="100%" height={HEIGHT} viewBox={`0 0 ${WIDTH} ${HEIGHT}`}>
        <Line x1={LEFT} y1={TOP} x2={RIGHT} y2={TOP} stroke={colors.border as string} />
        <Line x1={LEFT} y1={(TOP + BOTTOM) / 2} x2={RIGHT} y2={(TOP + BOTTOM) / 2} stroke={colors.border as string} />
        <Line x1={LEFT} y1={BOTTOM} x2={RIGHT} y2={BOTTOM} stroke={colors.border as string} />
        <SvgText x={LEFT - 7} y={TOP + 4} textAnchor="end" fontSize="9" fill={colors.muted as string}>{maximum.toFixed(2)}</SvgText>
        <SvgText x={LEFT - 7} y={(TOP + BOTTOM) / 2 + 4} textAnchor="end" fontSize="9" fill={colors.muted as string}>{((maximum + minimum) / 2).toFixed(2)}</SvgText>
        <SvgText x={LEFT - 7} y={BOTTOM + 4} textAnchor="end" fontSize="9" fill={colors.muted as string}>{minimum.toFixed(2)}</SvgText>
        {visibleSeries.map((item) => (
          <Polyline
            key={item.label}
            points={coordinates(item.points)}
            fill="none"
            stroke={item.color}
            strokeWidth="3"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        ))}
        {selectedPoints ? <>
          <SvgText x={LEFT} y="160" textAnchor="start" fontSize="8" fill={colors.muted as string}>{selectedPoints[0]?.date}</SvgText>
          <SvgText x={RIGHT} y="160" textAnchor="end" fontSize="8" fill={colors.muted as string}>{selectedPoints[selectedPoints.length - 1]?.date}</SvgText>
          <SvgText x={(LEFT + RIGHT) / 2} y="176" textAnchor="middle" fontSize="8" fontWeight="700" fill={colors.textSecondary as string}>Date</SvgText>
        </> : null}
        <SvgText x="4" y="10" fontSize="8" fontWeight="700" fill={colors.textSecondary as string}>Normalized value</SvgText>
      </Svg>
      <View style={styles.legend}>
        {series.map((item) => (
          <View key={item.label} style={styles.legendItem}>
            <View style={[styles.dot, { backgroundColor: item.color }]} />
            <Text style={styles.legendText}>{item.label}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  empty: { color: colors.muted, fontSize: 12 },
  controls: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.xs, marginBottom: spacing.sm },
  control: { minHeight: 34, justifyContent: 'center', paddingHorizontal: spacing.sm, borderWidth: 1, borderColor: colors.border, borderRadius: 10, backgroundColor: colors.surfaceAlt },
  controlSelected: { borderColor: colors.primary, backgroundColor: colors.cyanBackground },
  controlText: { color: colors.muted, fontSize: 10, fontWeight: '800' },
  controlTextSelected: { color: colors.text },
  legend: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md, marginTop: spacing.sm },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: spacing.xs },
  dot: { width: 8, height: 8, borderRadius: 4 },
  legendText: { color: colors.textSecondary, fontSize: 10, fontWeight: '700' }
});
