import { Ionicons } from '@expo/vector-icons';
import React from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Svg, { Circle, Path } from 'react-native-svg';

import { AuraMark } from '../../components/brand/AuraMark';
import { colors, spacing } from '../../theme/theme';

const features = [
  ['analytics-outline', 'Analyze\nPortfolio Risk'],
  ['pulse-outline', 'Run Historical\nSimulations'],
  ['document-text-outline', 'Save Analysis\nReports']
] as const;

function WelcomeBackdrop() {
  return (
    <Svg
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
      preserveAspectRatio="xMidYMid slice"
      style={StyleSheet.absoluteFill}
      viewBox="0 0 400 800"
    >
      <Circle
        cx="410"
        cy="-10"
        fill={colors.primary}
        fillOpacity="0.09"
        r="150"
        stroke={colors.primary}
        strokeOpacity="0.45"
      />
      <Path
        d="M-30 558C58 509 104 567 175 531C244 497 311 543 430 483"
        fill="none"
        stroke={colors.primary}
        strokeOpacity="0.15"
      />
      <Path
        d="M-30 596C61 543 120 604 187 562C256 520 328 584 430 521"
        fill="none"
        stroke={colors.cyan}
        strokeOpacity="0.1"
      />
    </Svg>
  );
}

function ProductPreview() {
  return (
    <View style={styles.preview}>
      <View style={styles.chartCard}>
        <Text style={styles.previewEyebrow}>PORTFOLIO ANALYTICS</Text>
        <Text style={styles.previewTitle}>Understand risk clearly</Text>
        <Svg height={76} viewBox="0 0 190 76" width="100%">
          <Path
            d="M3 65C22 58 28 61 42 47C55 34 68 55 84 39C100 22 112 42 130 27C146 14 157 28 174 10L188 3"
            fill="none"
            stroke={colors.primary}
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="3"
          />
          <Circle cx="188" cy="3" fill={colors.primarySoft} r="4" />
        </Svg>
      </View>

      <View style={styles.reportCard}>
        <Text style={styles.reportLabel}>SAVED REPORTS</Text>
        <View style={styles.ring}>
          <View style={styles.ringInner} />
        </View>
        <Text style={styles.reportTitle}>Portfolio analytics</Text>
        <Text style={styles.reportText}>Risk · Return · Drawdown</Text>
      </View>
    </View>
  );
}

export function WelcomeScreen({
  onGetStarted,
  onLogin
}: {
  onGetStarted: () => void;
  onLogin: () => void;
}) {
  return (
    <SafeAreaView style={styles.safe}>
      <WelcomeBackdrop />
      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.hero}>
          <AuraMark size={104} />
          <Text style={styles.brand}>Aura</Text>
          <Text style={styles.tagline}>Portfolio Risk Intelligence</Text>
          <View style={styles.accent} />
          <Text style={styles.description}>
            Turning complex financial data into clear portfolio risk education.
          </Text>
        </View>

        <ProductPreview />

        <View style={styles.features}>
          {features.map(([icon, label]) => (
            <View key={label} style={styles.feature}>
              <View style={styles.featureIcon}>
                <Ionicons color={colors.primary} name={icon} size={25} />
              </View>
              <Text style={styles.featureText}>{label}</Text>
            </View>
          ))}
        </View>

        <View style={styles.actions}>
          <Pressable
            accessibilityRole="button"
            onPress={onGetStarted}
            style={({ pressed }) => [
              styles.getStarted,
              pressed && styles.pressed
            ]}
          >
            <Text style={styles.getStartedText}>Get Started</Text>
            <Ionicons color={colors.onPrimary} name="arrow-forward" size={25} />
          </Pressable>

          <View style={styles.loginRow}>
            <Text style={styles.loginPrompt}>Already have an account?</Text>
            <Pressable
              accessibilityRole="button"
              hitSlop={6}
              onPress={onLogin}
              style={({ pressed }) => pressed && styles.pressed}
            >
              <Text style={styles.loginLink}>Log In</Text>
            </Pressable>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: {
    flexGrow: 1,
    justifyContent: 'space-between',
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.xl,
    paddingBottom: spacing.xxl,
    gap: spacing.xl
  },
  hero: { alignItems: 'center' },
  brand: {
    color: colors.text,
    fontSize: 44,
    lineHeight: 50,
    fontWeight: '900',
    marginTop: -10
  },
  tagline: {
    maxWidth: 310,
    color: colors.text,
    fontSize: 21,
    lineHeight: 28,
    fontWeight: '800',
    textAlign: 'center',
    marginTop: spacing.sm
  },
  accent: {
    width: 46,
    height: 3,
    borderRadius: 2,
    backgroundColor: colors.primary,
    marginVertical: spacing.md
  },
  description: {
    maxWidth: 330,
    color: colors.textSecondary,
    fontSize: 13,
    lineHeight: 19,
    textAlign: 'center'
  },
  preview: {
    minHeight: 190,
    justifyContent: 'center',
    marginHorizontal: spacing.sm
  },
  chartCard: {
    minHeight: 158,
    marginRight: 70,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.backgroundSoft,
    padding: spacing.lg
  },
  previewEyebrow: {
    color: colors.primary,
    fontSize: 8,
    fontWeight: '900',
    letterSpacing: 1
  },
  previewTitle: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '800',
    marginTop: spacing.xs,
    marginBottom: spacing.sm
  },
  reportCard: {
    position: 'absolute',
    right: 0,
    width: 138,
    minHeight: 176,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.primary,
    backgroundColor: colors.surface,
    padding: spacing.md
  },
  reportLabel: {
    color: colors.textSecondary,
    fontSize: 9,
    fontWeight: '900',
    letterSpacing: 0.8
  },
  ring: {
    width: 56,
    height: 56,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 28,
    borderWidth: 9,
    borderColor: colors.primary,
    borderLeftColor: colors.surfaceElevated,
    marginVertical: spacing.md
  },
  ringInner: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: colors.surface
  },
  reportTitle: { color: colors.text, fontSize: 12, fontWeight: '900' },
  reportText: {
    color: colors.textSecondary,
    fontSize: 9,
    textAlign: 'center',
    marginTop: spacing.xs
  },
  features: { flexDirection: 'row', justifyContent: 'space-between' },
  feature: { width: '31%', alignItems: 'center' },
  featureIcon: {
    width: 54,
    height: 54,
    alignItems: 'center',
    justifyContent: 'center'
  },
  featureText: {
    color: colors.textSecondary,
    fontSize: 11,
    lineHeight: 16,
    fontWeight: '700',
    textAlign: 'center',
    marginTop: spacing.sm
  },
  actions: { gap: spacing.lg },
  getStarted: {
    minHeight: 58,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.md,
    borderRadius: 29,
    backgroundColor: colors.primary
  },
  getStartedText: { color: colors.onPrimary, fontSize: 18, fontWeight: '900' },
  loginRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm
  },
  loginPrompt: { color: colors.textSecondary, fontSize: 13 },
  loginLink: { color: colors.primary, fontSize: 13, fontWeight: '900' },
  pressed: { opacity: 0.72 }
});
