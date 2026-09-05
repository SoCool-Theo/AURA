import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import Svg, { Line, Polyline } from 'react-native-svg';

import type { HistoricalScenarioTrajectoryPoint } from '../../types/simulation';
import { colors, spacing } from '../../theme/theme';

const WIDTH = 340;
const HEIGHT = 150;
const PADDING = 12;

export function SimulationTrajectoryChart({
  series
}: {
  series: Array<{
    label: string;
    color: string;
    points: HistoricalScenarioTrajectoryPoint[];
  }>;
}) {
  const values = series.flatMap((item) => item.points.map((point) => point.normalized_value));
  if (!values.length) return <Text style={styles.empty}>No trajectory observations returned.</Text>;

  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const range = maximum - minimum || 1;
  const longest = Math.max(...series.map((item) => item.points.length));
  const dates = series.find((item) => item.points.length === longest)?.points ?? [];

  function coordinates(points: HistoricalScenarioTrajectoryPoint[]): string {
    return points.map((point, index) => {
      const x = PADDING + (index / Math.max(points.length - 1, 1)) * (WIDTH - PADDING * 2);
      const y = PADDING + ((maximum - point.normalized_value) / range) * (HEIGHT - PADDING * 2);
      return `${x},${y}`;
    }).join(' ');
  }

  return (
    <View>
      <Svg width="100%" height={HEIGHT} viewBox={`0 0 ${WIDTH} ${HEIGHT}`}>
        <Line x1={PADDING} y1={HEIGHT - PADDING} x2={WIDTH - PADDING} y2={HEIGHT - PADDING} stroke={colors.border as string} />
        {series.map((item) => (
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
      </Svg>
      <View style={styles.dates}>
        <Text style={styles.date}>{dates[0]?.date}</Text>
        <Text style={styles.date}>{dates[dates.length - 1]?.date}</Text>
      </View>
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
  dates: { flexDirection: 'row', justifyContent: 'space-between' },
  date: { color: colors.muted, fontSize: 9 },
  legend: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md, marginTop: spacing.sm },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: spacing.xs },
  dot: { width: 8, height: 8, borderRadius: 4 },
  legendText: { color: colors.textSecondary, fontSize: 10, fontWeight: '700' }
});
