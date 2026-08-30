import React, { useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { PageTitle } from '../../components/ui/PageTitle';
import { SectionHeader } from '../../components/ui/SectionHeader';
import { Tag } from '../../components/ui/Tag';
import { AllocationChart } from '../../components/charts/AllocationChart';
import { useAppData } from '../../hooks/useAppData';
import { usePreferences } from '../../preferences/usePreferences';
import { demoAnalyzePortfolio } from '../../utils/localCalculations';
import { colors, spacing } from '../../theme/theme';
import { formatCurrency, formatPercent } from '../../utils/formatting';

export function PortfolioDetailScreen({ route, navigation }: { route: any; navigation: any }) {
  const { hidePortfolioValues } = usePreferences();
  const {
    portfolios,
    renamePortfolio,
    duplicatePortfolio,
    deletePortfolio,
    setActivePortfolio
  } = useAppData();

  const portfolio = portfolios.find((item) => item.id === route.params.portfolioId);
  const [editingName, setEditingName] = useState(false);
  const [name, setName] = useState(portfolio?.name ?? '');

  if (!portfolio) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.notFound}><Text style={styles.notFoundText}>Portfolio not found.</Text></View>
      </SafeAreaView>
    );
  }

  const selectedPortfolio = portfolio;
  const analysis = demoAnalyzePortfolio(selectedPortfolio);

  async function duplicate() {
    const copy = await duplicatePortfolio(selectedPortfolio.id);
    if (copy) navigation.replace('PortfolioDetail', { portfolioId: copy.id });
  }

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content}>
        {editingName ? (
          <View style={styles.renameArea}>
            <Input label="Portfolio name" value={name} onChangeText={setName} autoCapitalize="words" />
            <View style={styles.inline}>
              <Button title="Save" style={{ flex: 1 }} onPress={async () => {
                await renamePortfolio(selectedPortfolio.id, name);
                setEditingName(false);
              }} />
              <Button title="Cancel" variant="secondary" style={{ flex: 1 }} onPress={() => setEditingName(false)} />
            </View>
          </View>
        ) : (
          <PageTitle
            title={selectedPortfolio.name}
            subtitle={`${selectedPortfolio.holdings.length} assets · ${hidePortfolioValues ? '••••••' : formatCurrency(selectedPortfolio.totalValue)}`}
            right={
              <Pressable style={styles.iconButton} onPress={() => setEditingName(true)}>
                <Ionicons name="settings-outline" color={colors.textSecondary} size={20} />
              </Pressable>
            }
          />
        )}

        <Card style={styles.riskCard}>
          <View style={styles.riskLeft}>
            <Text style={styles.overline}>RISK SCORE</Text>
            <Text style={styles.riskNumber}>{analysis.riskScore}</Text>
            <Text style={styles.outOf}>/100</Text>
            <Tag label={analysis.riskLevel} tone={analysis.riskScore >= 70 ? 'danger' : 'warning'} />
          </View>

          <View style={styles.divider} />

          <View style={styles.metrics}>
            <View style={styles.metricRow}>
              <Text style={styles.metricLabel}>Volatility</Text>
              <Text style={styles.metricValue}>{formatPercent(analysis.volatility)}</Text>
            </View>
            <View style={styles.metricRow}>
              <Text style={styles.metricLabel}>Sharpe ratio</Text>
              <Text style={styles.metricValue}>{analysis.sharpeRatio.toFixed(2)}</Text>
            </View>
            <View style={styles.metricRow}>
              <Text style={styles.metricLabel}>Max drawdown</Text>
              <Text style={[styles.metricValue, { color: colors.danger }]}>{formatPercent(analysis.maxDrawdown)}</Text>
            </View>
            <View style={styles.metricRow}>
              <Text style={styles.metricLabel}>Diversification</Text>
              <Text style={styles.metricValue}>{analysis.diversification}</Text>
            </View>
          </View>
        </Card>

        <View style={styles.actions}>
          <Button
            title="Analyze"
            style={{ flex: 1 }}
            onPress={() => navigation.navigate('PortfolioAnalysis', { portfolioId: selectedPortfolio.id })}
          />
          <Button
            title="Add asset"
            variant="secondary"
            style={{ flex: 1 }}
            onPress={() => navigation.navigate('AddAsset', { portfolioId: selectedPortfolio.id })}
          />
        </View>

        <SectionHeader title="Allocation" action="Edit holdings" onPress={() =>
          navigation.navigate('EditHoldings', { portfolioId: selectedPortfolio.id })
        } />
        <Card>
          <AllocationChart data={selectedPortfolio.holdings.map((h) => ({ symbol: h.symbol, weight: h.weight }))} />
        </Card>

        <SectionHeader title="Holdings" />
        <View style={styles.holdingsList}>
          {selectedPortfolio.holdings.map((holding) => (
            <Card key={holding.symbol} style={styles.holdingCard}>
              <View style={styles.symbolBadge}>
                <Text style={styles.symbolBadgeText}>{holding.symbol.slice(0, 4)}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.holdingSymbol}>{holding.symbol}</Text>
                <Text style={styles.holdingName}>{holding.name}</Text>
              </View>
              <View style={styles.holdingRight}>
                <Text style={styles.holdingValue}>{hidePortfolioValues ? '••••••' : formatCurrency(holding.value)}</Text>
                <Text style={styles.holdingWeight}>{holding.weight.toFixed(1)}%</Text>
              </View>
            </Card>
          ))}
        </View>

        <SectionHeader title="Portfolio actions" />
        <View style={styles.inline}>
          <Button title="Duplicate" variant="secondary" style={{ flex: 1 }} onPress={duplicate} />
          <Button title="Set active" variant="secondary" style={{ flex: 1 }} onPress={() => setActivePortfolio(selectedPortfolio.id)} />
        </View>
        <Button
          title="Delete portfolio"
          variant="danger"
          style={{ marginTop: spacing.md }}
          onPress={() => Alert.alert('Delete portfolio?', 'This removes the local portfolio.', [
            { text: 'Cancel', style: 'cancel' },
            {
              text: 'Delete',
              style: 'destructive',
              onPress: async () => {
                await deletePortfolio(selectedPortfolio.id);
                navigation.popToTop();
              }
            }
          ])}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 100 },
  iconButton: { width: 40, height: 40, borderRadius: 13, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, alignItems: 'center', justifyContent: 'center' },
  renameArea: { gap: spacing.md },
  inline: { flexDirection: 'row', gap: spacing.md },
  riskCard: { marginTop: spacing.xl, flexDirection: 'row', gap: spacing.lg, alignItems: 'stretch' },
  riskLeft: { width: 110, alignItems: 'center', justifyContent: 'center', gap: 3 },
  overline: { color: colors.muted, fontSize: 9, fontWeight: '900', letterSpacing: 1 },
  riskNumber: { color: colors.text, fontSize: 42, fontWeight: '900' },
  outOf: { color: colors.muted, fontSize: 11, marginTop: -6 },
  divider: { width: 1, backgroundColor: colors.borderSoft },
  metrics: { flex: 1, gap: spacing.md },
  metricRow: { flexDirection: 'row', justifyContent: 'space-between', gap: spacing.md },
  metricLabel: { color: colors.muted, fontSize: 11 },
  metricValue: { color: colors.text, fontSize: 12, fontWeight: '900' },
  actions: { flexDirection: 'row', gap: spacing.md, marginTop: spacing.md },
  holdingsList: { gap: spacing.sm },
  holdingCard: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, paddingVertical: spacing.md },
  symbolBadge: { width: 42, height: 42, borderRadius: 13, backgroundColor: colors.surfaceAlt, alignItems: 'center', justifyContent: 'center' },
  symbolBadgeText: { color: colors.primary, fontWeight: '900', fontSize: 10 },
  holdingSymbol: { color: colors.text, fontWeight: '900' },
  holdingName: { color: colors.muted, fontSize: 11, marginTop: 3 },
  holdingRight: { alignItems: 'flex-end' },
  holdingValue: { color: colors.text, fontWeight: '900' },
  holdingWeight: { color: colors.primary, fontSize: 11, marginTop: 3 },
  notFound: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  notFoundText: { color: colors.textSecondary }
});
