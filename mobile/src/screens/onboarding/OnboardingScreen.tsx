import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Button } from '../../components/ui/Button';
import { RiskGauge } from '../../components/charts/RiskGauge';
import { colors, spacing, typography } from '../../theme/theme';

export function OnboardingScreen({ onFinish }: { onFinish: () => void }) {
  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.content}>
        <Text style={styles.eyebrow}>AURA</Text>
        <RiskGauge score={78} />
        <Text style={styles.title}>Understand Your Portfolio Risk</Text>
        <Text style={styles.subtitle}>
          Aura helps you understand portfolio risk using data, historical simulations, and simple explanations.
        </Text>
        <View style={styles.spacer} />
        <Button title="Get started →" onPress={onFinish} />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { flex: 1, padding: spacing.xl, alignItems: 'center', justifyContent: 'center', gap: spacing.xl },
  eyebrow: { color: colors.primary, fontWeight: '900', letterSpacing: 2 },
  title: { color: colors.text, ...typography.h1, textAlign: 'center' },
  subtitle: { color: colors.textSecondary, textAlign: 'center', lineHeight: 22 },
  spacer: { height: spacing.lg, width: '100%' }
});
