import React from 'react';
import { View } from 'react-native';
import Svg, { Polyline } from 'react-native-svg';
import { colors } from '../../theme/colors';

export function LineChart() {
  return (
    <View style={{ height: 130, width: '100%' }}>
      <Svg width="100%" height="130" viewBox="0 0 320 130">
        <Polyline
          points="0,98 35,90 70,102 105,70 140,76 175,55 210,62 245,40 280,48 320,22"
          fill="none"
          stroke={colors.primary}
          strokeWidth="4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    </View>
  );
}
