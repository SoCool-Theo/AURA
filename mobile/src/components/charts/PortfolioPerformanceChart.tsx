import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import Svg, { Line, Polyline } from 'react-native-svg';
import { colors, spacing } from '../../theme/theme';

const portfolio = '8,118 40,107 72,111 103,90 135,96 166,72 198,77 229,53 261,59 292,35 324,42 356,18';
const benchmark = '8,121 40,116 72,119 103,108 135,110 166,95 198,98 229,83 261,86 292,70 324,65 356,55';

export function PortfolioPerformanceChart() {
  return (
    <View>
      <View style={styles.legend}>
        <View style={styles.legendItem}><View style={[styles.dot, { backgroundColor: colors.primary }]} /><Text style={styles.legendText}>Your Portfolio</Text></View>
        <View style={styles.legendItem}><View style={[styles.dot, { backgroundColor: colors.muted }]} /><Text style={styles.legendText}>Benchmark</Text></View>
      </View>
      <View style={styles.chart}>
        <Svg width="100%" height="150" viewBox="0 0 364 140">
          {[25, 55, 85, 115].map((y) => <Line key={y} x1="0" y1={y} x2="364" y2={y} stroke={colors.borderSoft} strokeWidth="1" />)}
          <Polyline points={benchmark} fill="none" stroke={colors.muted} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          <Polyline points={portfolio} fill="none" stroke={colors.primary} strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" />
        </Svg>
      </View>
      <View style={styles.axis}><Text style={styles.axisText}>Jun</Text><Text style={styles.axisText}>Sep</Text><Text style={styles.axisText}>Dec</Text><Text style={styles.axisText}>Mar</Text><Text style={styles.axisText}>May</Text></View>
    </View>
  );
}

const styles = StyleSheet.create({
  legend: { flexDirection: 'row', gap: spacing.lg, marginBottom: spacing.sm },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  dot: { width: 7, height: 7, borderRadius: 4 },
  legendText: { color: colors.textSecondary, fontSize: 10, fontWeight: '700' },
  chart: { height: 150 },
  axis: { flexDirection: 'row', justifyContent: 'space-between', marginTop: -6 },
  axisText: { color: colors.muted, fontSize: 9 }
});
