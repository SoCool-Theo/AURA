import React, { useMemo } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import Svg, { Line, Polyline } from 'react-native-svg';

import type {
  AssetReturnPoint,
  PortfolioReturnPoint
} from '../../types/analytics';
import { colors, spacing } from '../../theme/theme';
import { formatRatioPercent } from '../../report/reportFormatting';

const WIDTH = 320;
const HEIGHT = 130;
const PADDING = 12;

export function PortfolioReturnsChart({
  points,
  emptyMessage = 'No return observations are available.'
}: {
  points: Array<PortfolioReturnPoint | AssetReturnPoint>;
  emptyMessage?: string;
}) {
  const chart = useMemo(() => {
    if (!points.length) return null;
    const values = points.map(returnValue);
    const minimum = Math.min(...values, 0);
    const maximum = Math.max(...values, 0);
    const range = maximum - minimum || 1;
    const usableWidth = WIDTH - PADDING * 2;
    const usableHeight = HEIGHT - PADDING * 2;
    const coordinates = points.map((point, index) => {
      const x = PADDING + (
        points.length === 1 ? usableWidth / 2 : (index / (points.length - 1)) * usableWidth
      );
      const y = PADDING + ((maximum - returnValue(point)) / range) * usableHeight;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    }).join(' ');
    const zeroY = PADDING + ((maximum - 0) / range) * usableHeight;
    return { coordinates, zeroY, minimum, maximum };
  }, [points]);

  if (!chart) {
    return <Text style={styles.empty}>{emptyMessage}</Text>;
  }

  return (
    <View>
      <View style={styles.rangeRow}>
        <Text style={styles.rangeText}>{formatRatioPercent(chart.maximum, 3)}</Text>
        <Text style={styles.rangeText}>{formatRatioPercent(chart.minimum, 3)}</Text>
      </View>
      <Svg width="100%" height={HEIGHT} viewBox={`0 0 ${WIDTH} ${HEIGHT}`}>
        <Line
          x1={PADDING}
          y1={chart.zeroY}
          x2={WIDTH - PADDING}
          y2={chart.zeroY}
          stroke={colors.border}
          strokeWidth="1"
        />
        <Polyline
          points={chart.coordinates}
          fill="none"
          stroke={colors.primary}
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
      <View style={styles.axis}>
        <Text style={styles.axisText}>{points[0].date}</Text>
        <Text style={styles.axisText}>{points[points.length - 1].date}</Text>
      </View>
    </View>
  );
}

function returnValue(point: PortfolioReturnPoint | AssetReturnPoint): number {
  return 'portfolio_return' in point
    ? point.portfolio_return
    : point.asset_return;
}

const styles = StyleSheet.create({
  rangeRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.xs
  },
  rangeText: { color: colors.muted, fontSize: 9 },
  axis: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: spacing.xs
  },
  axisText: { color: colors.muted, fontSize: 9 },
  empty: { color: colors.muted, textAlign: 'center', paddingVertical: spacing.xl }
});
