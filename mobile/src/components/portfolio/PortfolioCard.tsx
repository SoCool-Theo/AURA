import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import type { PortfolioSummaryResponse } from '../../types/portfolio';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { colors, spacing } from '../../theme/theme';

export function PortfolioCard({
  portfolio,
  active,
  onPress,
  onOpenReport
}: {
  portfolio: PortfolioSummaryResponse;
  active: boolean;
  onPress: () => void;
  onOpenReport?: () => void;
}) {
  return (
    <Card style={[styles.card, active && styles.activeCard]}>
      <Pressable
        accessibilityLabel={`Open ${portfolio.name} portfolio${active ? ', active' : ''}`}
        accessibilityRole="button"
        accessibilityState={{ selected: active }}
        onPress={onPress}
        style={styles.details}
      >
        <View style={styles.top}>
          <View style={styles.main}>
            <Text style={styles.name}>{portfolio.name}</Text>
            <Text style={styles.meta}>
              {portfolio.portfolio_type === 'PLANNED'
                ? `Planned in ${portfolio.plan_currency}`
                : portfolio.portfolio_type === 'LEGACY'
                  ? 'Legacy allocation'
                  : 'Current holdings'} · Updated {new Date(portfolio.updated_at).toLocaleDateString()}
            </Text>
          </View>
          {active ? <Text style={styles.activeLabel}>ACTIVE</Text> : null}
        </View>
        <Text style={styles.created}>
          Created {new Date(portfolio.created_at).toLocaleDateString()}
        </Text>
      </Pressable>
      {onOpenReport ? (
        <Button
          title="View Latest Report"
          variant="secondary"
          onPress={onOpenReport}
        />
      ) : null}
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { gap: spacing.md },
  details: { minHeight: 56, gap: spacing.md, justifyContent: 'center' },
  activeCard: { borderColor: colors.primary },
  top: { flexDirection: 'row', alignItems: 'center', gap: spacing.lg },
  main: { flex: 1 },
  name: { color: colors.text, fontSize: 18, fontWeight: '800' },
  meta: { color: colors.textSecondary, marginTop: 4, fontSize: 12 },
  created: { color: colors.muted, fontSize: 11 },
  activeLabel: { color: colors.success, fontSize: 9, fontWeight: '900', letterSpacing: 0.8 }
});
