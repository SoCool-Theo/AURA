import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import type { Portfolio } from '../../types/portfolio';
import { Card } from '../ui/Card';
import { RiskBadge } from '../ui/RiskBadge';
import { colors, spacing } from '../../theme/theme';
import { formatCurrency } from '../../utils/formatting';

export function PortfolioCard({ portfolio, onPress }: { portfolio: Portfolio; onPress: () => void }) {
  return (
    <Pressable onPress={onPress}>
      <Card style={styles.card}>
        <View style={styles.top}>
          <View>
            <Text style={styles.name}>{portfolio.name}</Text>
            <Text style={styles.value}>{formatCurrency(portfolio.totalValue)}</Text>
          </View>
          <RiskBadge level={portfolio.riskLevel} />
        </View>
        <View style={styles.stats}>
          <Text style={styles.stat}>Risk {portfolio.riskScore}/100</Text>
          <Text style={styles.stat}>Return {portfolio.annualizedReturn.toFixed(1)}%</Text>
          <Text style={styles.stat}>{portfolio.holdings.length} assets</Text>
        </View>
      </Card>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: { gap: spacing.lg },
  top: { flexDirection: 'row', justifyContent: 'space-between', gap: spacing.lg },
  name: { color: colors.text, fontSize: 18, fontWeight: '800' },
  value: { color: colors.textSecondary, marginTop: 4 },
  stats: { flexDirection: 'row', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 },
  stat: { color: colors.muted, fontSize: 12, fontWeight: '700' }
});
