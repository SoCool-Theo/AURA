import React from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Svg, {
  Circle,
  Defs,
  LinearGradient,
  Path,
  Rect,
  Stop
} from 'react-native-svg';

import { AuraMark } from '../../components/brand/AuraMark';
import { colors, spacing } from '../../theme/theme';

function SplashArtwork() {
  return (
    <Svg
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
      preserveAspectRatio="xMidYMid slice"
      style={StyleSheet.absoluteFill}
      viewBox="0 0 400 800"
    >
      <Defs>
        <LinearGradient id="auraGlow" x1="0" x2="1" y1="0" y2="1">
          <Stop offset="0" stopColor={colors.primarySoft} stopOpacity="0.42" />
          <Stop offset="1" stopColor={colors.cyan} stopOpacity="0.02" />
        </LinearGradient>
        <LinearGradient id="waveGlow" x1="0" x2="0" y1="0" y2="1">
          <Stop offset="0" stopColor={colors.primary} stopOpacity="0.28" />
          <Stop offset="1" stopColor={colors.background} stopOpacity="0" />
        </LinearGradient>
      </Defs>

      <Circle cx="-18" cy="168" fill="url(#auraGlow)" r="150" />

      <Path d="M252 128V244" stroke={colors.primary} strokeOpacity="0.12" />
      <Rect fill={colors.primary} fillOpacity="0.12" height="35" rx="2" width="9" x="248" y="172" />
      <Path d="M278 110V225" stroke={colors.primary} strokeOpacity="0.18" />
      <Rect fill={colors.primary} fillOpacity="0.2" height="43" rx="2" width="10" x="273" y="151" />
      <Path d="M305 92V211" stroke={colors.primary} strokeOpacity="0.22" />
      <Rect fill={colors.primary} fillOpacity="0.25" height="31" rx="2" width="10" x="300" y="132" />
      <Path d="M332 73V193" stroke={colors.primary} strokeOpacity="0.28" />
      <Rect fill={colors.primary} fillOpacity="0.32" height="45" rx="2" width="10" x="327" y="105" />
      <Path d="M359 55V176" stroke={colors.primary} strokeOpacity="0.34" />
      <Rect fill={colors.primary} fillOpacity="0.4" height="38" rx="2" width="10" x="354" y="84" />
      <Path d="M386 40V159" stroke={colors.primary} strokeOpacity="0.4" />
      <Rect fill={colors.primary} fillOpacity="0.48" height="46" rx="2" width="10" x="381" y="62" />

      <Path
        d="M-30 612C44 570 82 590 135 559C194 524 245 530 292 553C339 576 377 561 430 519V810H-30Z"
        fill="url(#waveGlow)"
      />
      <Path
        d="M-28 620C40 579 87 596 139 564C196 529 245 538 292 560C340 582 382 566 430 526"
        fill="none"
        stroke={colors.primary}
        strokeOpacity="0.56"
        strokeWidth="1.2"
      />
      <Path
        d="M-35 665C23 626 82 636 133 612C191 584 241 590 291 616C337 639 383 630 435 586"
        fill="none"
        stroke={colors.cyan}
        strokeDasharray="1 7"
        strokeLinecap="round"
        strokeOpacity="0.32"
        strokeWidth="2"
      />
      <Path d="M48 552V693" stroke={colors.primary} strokeOpacity="0.25" />
      <Circle cx="48" cy="552" fill={colors.primary} fillOpacity="0.65" r="3" />
      <Path d="M342 575V718" stroke={colors.primary} strokeOpacity="0.28" />
      <Circle cx="342" cy="575" fill={colors.primary} fillOpacity="0.72" r="3" />
    </Svg>
  );
}

export function SplashScreen() {
  return (
    <SafeAreaView style={styles.safe}>
      <SplashArtwork />
      <View accessibilityLabel="Aura is starting" style={styles.content}>
        <View style={styles.brandBlock}>
          <AuraMark />
          <Text style={styles.brand}>Aura</Text>
          <Text style={styles.tagline}>Portfolio Risk Intelligence</Text>
          <View style={styles.accent} />
          <Text style={styles.description}>
            Turning complex financial data into clear portfolio risk education.
          </Text>
        </View>

        <View style={styles.loadingBlock}>
          <ActivityIndicator color={colors.primary} size="large" />
          <Text style={styles.loadingText}>Loading Aura…</Text>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    overflow: 'hidden',
    backgroundColor: colors.background
  },
  content: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.xxl,
    paddingTop: 90,
    paddingBottom: 60
  },
  brandBlock: { alignItems: 'center', maxWidth: 330 },
  brand: {
    color: colors.text,
    fontSize: 58,
    lineHeight: 66,
    fontWeight: '900',
    letterSpacing: 0.5,
    marginTop: -8
  },
  tagline: {
    color: colors.text,
    fontSize: 21,
    lineHeight: 28,
    fontWeight: '800',
    textAlign: 'center',
    marginTop: spacing.md
  },
  accent: {
    width: 48,
    height: 3,
    borderRadius: 2,
    backgroundColor: colors.primary,
    marginVertical: spacing.lg
  },
  description: {
    color: colors.textSecondary,
    fontSize: 14,
    lineHeight: 21,
    textAlign: 'center'
  },
  loadingBlock: { alignItems: 'center', gap: spacing.md },
  loadingText: {
    color: colors.textSecondary,
    fontSize: 13,
    fontWeight: '700'
  }
});
