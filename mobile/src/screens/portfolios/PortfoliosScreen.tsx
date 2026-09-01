import React, { useMemo, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import { Card } from '../../components/ui/Card';
import { PageTitle } from '../../components/ui/PageTitle';
import { RiskBadge } from '../../components/ui/RiskBadge';
import { useAppData } from '../../hooks/useAppData';
import { usePreferences } from '../../preferences/usePreferences';
import { demoAnalyzePortfolio } from '../../utils/localCalculations';
import { colors, spacing } from '../../theme/theme';
import { formatCurrency, formatPercent } from '../../utils/formatting';

export function PortfoliosScreen({ navigation }: { navigation: any }) {
  const { portfolios, activePortfolioId, setActivePortfolio } = useAppData();
  const { hidePortfolioValues } = usePreferences();
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return portfolios;
    return portfolios.filter((item) => item.name.toLowerCase().includes(q));
  }, [portfolios, query]);

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <PageTitle
          title="My Portfolios"
          subtitle="Create and manage your investment portfolios."
          right={
            <Pressable style={styles.newButton} onPress={() => navigation.navigate('CreatePortfolio')}>
              <Ionicons name="add" size={19} color={colors.onPrimary} />
            </Pressable>
          }
        />

        <View style={styles.searchBar}>
          <Ionicons name="search-outline" size={17} color={colors.muted} />
          <TextInput value={query} onChangeText={setQuery} placeholder="Search portfolios" placeholderTextColor={colors.muted} style={styles.searchInput} />
        </View>

        <View style={styles.tableHeader}>
          <Text style={[styles.headerText, { flex: 1.8 }]}>Portfolio</Text>
          <Text style={styles.headerText}>Risk</Text>
          <Text style={styles.headerText}>Return</Text>
        </View>

        <View style={styles.list}>
          {filtered.map((portfolio) => {
            const analysis = demoAnalyzePortfolio(portfolio);
            const active = portfolio.id === activePortfolioId;
            return (
              <Pressable
                key={portfolio.id}
                onPress={async () => {
                  await setActivePortfolio(portfolio.id);
                  navigation.navigate('PortfolioDetail', { portfolioId: portfolio.id });
                }}
              >
                <Card style={[styles.portfolioRow, active && styles.activeRow]}>
                  <View style={styles.portfolioMain}>
                    <View style={styles.portfolioIcon}><Ionicons name="briefcase-outline" size={19} color={colors.primary} /></View>
                    <View style={{ flex: 1 }}>
                      <View style={styles.nameLine}>
                        <Text style={styles.name}>{portfolio.name}</Text>
                        {active ? <Text style={styles.activeLabel}>ACTIVE</Text> : null}
                      </View>
                      <Text style={styles.value}>{hidePortfolioValues ? '••••••' : formatCurrency(portfolio.totalValue)}</Text>
                      <Text style={styles.updated}>{portfolio.holdings.length} holdings · Local demo</Text>
                    </View>
                  </View>
                  <View style={styles.compactMetrics}>
                    <View style={styles.metricCell}>
                      <Text style={styles.metricValue}>{analysis.riskScore}</Text>
                      <RiskBadge level={analysis.riskLevel} />
                    </View>
                    <View style={styles.metricCell}>
                      <Text style={[styles.returnValue, { color: analysis.annualizedReturn >= 0 ? colors.success : colors.danger }]}>{formatPercent(analysis.annualizedReturn)}</Text>
                      <Text style={styles.metricLabel}>Annualized</Text>
                    </View>
                    <Ionicons name="chevron-forward" size={18} color={colors.muted} />
                  </View>
                </Card>
              </Pressable>
            );
          })}
        </View>

        <Pressable onPress={() => navigation.navigate('CreatePortfolio')}>
          <Card style={styles.createCta}>
            <View style={{ flex: 1 }}>
              <Text style={styles.ctaEyebrow}>CREATE NEW PORTFOLIO</Text>
              <Text style={styles.ctaTitle}>Start building a new portfolio from scratch.</Text>
              <View style={styles.ctaLink}><Ionicons name="add-circle-outline" size={16} color={colors.primary} /><Text style={styles.ctaLinkText}>Create Portfolio</Text></View>
            </View>
            <View style={styles.ctaArt}>
              <View style={[styles.bar, { height: 28 }]} />
              <View style={[styles.bar, { height: 45 }]} />
              <View style={[styles.bar, { height: 62 }]} />
            </View>
          </Card>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 110 },
  newButton: { width: 40, height: 40, borderRadius: 12, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  searchBar: { height: 44, flexDirection: 'row', alignItems: 'center', gap: spacing.sm, paddingHorizontal: spacing.md, borderRadius: 13, backgroundColor: colors.surfaceAlt, borderWidth: 1, borderColor: colors.borderSoft, marginTop: spacing.xl },
  searchInput: { flex: 1, color: colors.text, fontSize: 12 },
  tableHeader: { flexDirection: 'row', marginTop: spacing.xl, paddingHorizontal: spacing.sm, gap: spacing.sm },
  headerText: { color: colors.muted, fontSize: 9, fontWeight: '900', textTransform: 'uppercase', letterSpacing: 0.8 },
  list: { gap: spacing.md, marginTop: spacing.sm },
  portfolioRow: { gap: spacing.md },
  activeRow: { borderColor: colors.primary },
  portfolioMain: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  portfolioIcon: { width: 44, height: 44, borderRadius: 14, backgroundColor: colors.cyanBackground, alignItems: 'center', justifyContent: 'center' },
  nameLine: { flexDirection: 'row', gap: spacing.sm, alignItems: 'center' },
  name: { color: colors.text, fontSize: 15, fontWeight: '900', flexShrink: 1 },
  activeLabel: { color: colors.success, fontSize: 8, fontWeight: '900', letterSpacing: 0.8 },
  value: { color: colors.textSecondary, fontSize: 12, fontWeight: '800', marginTop: 4 },
  updated: { color: colors.muted, fontSize: 9, marginTop: 4 },
  compactMetrics: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', borderTopWidth: 1, borderTopColor: colors.borderSoft, paddingTop: spacing.md },
  metricCell: { gap: 5 },
  metricValue: { color: colors.text, fontSize: 18, fontWeight: '900' },
  returnValue: { fontSize: 14, fontWeight: '900' },
  metricLabel: { color: colors.muted, fontSize: 9 },
  createCta: { marginTop: spacing.xl, flexDirection: 'row', alignItems: 'center', gap: spacing.xl, borderStyle: 'dashed', borderColor: colors.primary },
  ctaEyebrow: { color: colors.primary, fontSize: 9, fontWeight: '900', letterSpacing: 1 },
  ctaTitle: { color: colors.text, fontSize: 17, fontWeight: '900', lineHeight: 22, marginTop: 6 },
  ctaLink: { flexDirection: 'row', gap: 6, alignItems: 'center', marginTop: spacing.md },
  ctaLinkText: { color: colors.primary, fontSize: 11, fontWeight: '900' },
  ctaArt: { width: 74, height: 70, flexDirection: 'row', alignItems: 'flex-end', gap: 5, justifyContent: 'center' },
  bar: { width: 13, borderRadius: 5, backgroundColor: colors.primary }
});
