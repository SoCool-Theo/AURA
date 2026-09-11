import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import { colors, spacing } from '../../theme/theme';

const chartColors = [colors.primary, colors.purpleSoft, colors.blue, colors.warning, colors.success, colors.muted];

export function DonutAllocationChart({ data }: { data: Array<{ symbol: string; weight: number }> }) {
  const total = Math.max(1, data.reduce((sum, item) => sum + item.weight, 0));
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;

  return (
    <View style={styles.wrap}>
      <View style={styles.donutWrap}>
        <Svg width="120" height="120" viewBox="0 0 120 120">
          <Circle cx="60" cy="60" r={radius} stroke={colors.borderSoft} strokeWidth="16" fill="none" />
          {data.slice(0, 6).map((item, index) => {
            const fraction = item.weight / total;
            const dash = circumference * fraction;
            const gap = circumference - dash;
            const currentOffset = offset;
            offset -= dash;
            return (
              <Circle
                key={item.symbol}
                cx="60"
                cy="60"
                r={radius}
                stroke={chartColors[index % chartColors.length]}
                strokeWidth="16"
                fill="none"
                strokeDasharray={`${dash} ${gap}`}
                strokeDashoffset={currentOffset}
                strokeLinecap="butt"
                rotation="-90"
                origin="60,60"
              />
            );
          })}
        </Svg>
        <View style={styles.center}><Text style={styles.centerValue}>{data.length}</Text><Text style={styles.centerLabel}>Assets</Text></View>
      </View>

      <View style={styles.legend}>
        {data.slice(0, 6).map((item, index) => (
          <View key={item.symbol} style={styles.row}>
            <View style={[styles.swatch, { backgroundColor: chartColors[index % chartColors.length] }]} />
            <Text style={styles.symbol}>{item.symbol}</Text>
            <Text style={styles.weight}>{item.weight.toFixed(1)}%</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { flexDirection: 'row', gap: spacing.lg, alignItems: 'center' },
  donutWrap: { width: 120, height: 120, alignItems: 'center', justifyContent: 'center' },
  center: { position: 'absolute', alignItems: 'center' },
  centerValue: { color: colors.text, fontSize: 22, fontWeight: '900' },
  centerLabel: { color: colors.muted, fontSize: 9, marginTop: 1 },
  legend: { flex: 1, gap: spacing.sm },
  row: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  swatch: { width: 8, height: 8, borderRadius: 4 },
  symbol: { color: colors.textSecondary, flex: 1, fontSize: 11, fontWeight: '800' },
  weight: { color: colors.text, fontSize: 11, fontWeight: '900' }
});
