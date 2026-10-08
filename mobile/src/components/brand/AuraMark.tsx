import React from 'react';
import Svg, { Defs, LinearGradient, Path, Stop } from 'react-native-svg';

import { colors } from '../../theme/theme';

export function AuraMark({ size = 150 }: { size?: number }) {
  return (
    <Svg
      accessibilityElementsHidden
      height={size * 0.947}
      importantForAccessibility="no-hide-descendants"
      viewBox="0 0 150 142"
      width={size}
    >
      <Defs>
        <LinearGradient id="markGradient" x1="0" x2="1" y1="0" y2="1">
          <Stop offset="0" stopColor={colors.primarySoft} />
          <Stop offset="0.55" stopColor={colors.primary} />
          <Stop offset="1" stopColor={colors.cyan} />
        </LinearGradient>
      </Defs>
      <Path
        d="M75 6L145 134L101 107L75 58L49 107L5 134L75 6Z"
        fill="url(#markGradient)"
      />
      <Path d="M75 58L101 107L75 93L49 107L75 58Z" fill={colors.background} />
    </Svg>
  );
}
