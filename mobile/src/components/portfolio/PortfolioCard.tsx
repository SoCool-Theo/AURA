import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import type { PortfolioSummaryResponse } from '../../types/portfolio';
import { Card } from '../ui/Card';
import { colors, spacing } from '../../theme/theme';

export function PortfolioCard({
  portfolio,
  active,
  onPress
}: {
  portfolio: PortfolioSummaryResponse;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityLabel={`${portfolio.name} portfolio${active ? ', active' : ''}`}
      accessibilityRole="button"
      accessibilityState={{ selected: active }}
      onPress={onPress}
    >
      <Card style={[styles.card, active && styles.activeCard]}>
        <View style={styles.top}>
          <View style={styles.main}>
            <Text style={styles.name}>{portfolio.name}</Text>
            <Text style={styles.meta}>
              Updated {new Date(portfolio.updated_at).toLocaleDateString()}
            </Text>
          </View>
          {active ? <Text style={styles.activeLabel}>ACTIVE</Text> : null}
        </View>
        <Text style={styles.created}>
          Created {new Date(portfolio.created_at).toLocaleDateString()}
        </Text>
      </Card>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: { gap: spacing.md },
  activeCard: { borderColor: colors.primary },
  top: { flexDirection: 'row', alignItems: 'center', gap: spacing.lg },
  main: { flex: 1 },
  name: { color: colors.text, fontSize: 18, fontWeight: '800' },
  meta: { color: colors.textSecondary, marginTop: 4, fontSize: 12 },
  created: { color: colors.muted, fontSize: 11 },
  activeLabel: { color: colors.success, fontSize: 9, fontWeight: '900', letterSpacing: 0.8 }
});
