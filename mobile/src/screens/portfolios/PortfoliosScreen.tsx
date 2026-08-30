import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Card } from '../../components/ui/Card';
import { PageTitle } from '../../components/ui/PageTitle';
import { Tag } from '../../components/ui/Tag';
import { useAppData } from '../../hooks/useAppData';
import { usePreferences } from '../../preferences/usePreferences';
import { demoAnalyzePortfolio } from '../../utils/localCalculations';
import { colors, spacing } from '../../theme/theme';
import { formatCurrency, formatPercent } from '../../utils/formatting';

const tones = [
  { bg: colors.purpleBackground, fg: colors.purpleSoft, icon: 'trending-up-outline' as const },
  { bg: colors.positiveBackground, fg: colors.success, icon: 'cash-outline' as const },
  { bg: colors.blueBackground, fg: colors.blue, icon: 'scale-outline' as const }
];

export function PortfoliosScreen({ navigation }: { navigation: any }) {
  const { portfolios, activePortfolioId, setActivePortfolio } = useAppData();
  const { hidePortfolioValues } = usePreferences();

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content}>
        <PageTitle
          title="Portfolios"
          subtitle="Your saved portfolios and local demo values."
          right={
            <Pressable style={styles.addButton} onPress={() => navigation.navigate('CreatePortfolio')}>
              <Ionicons name="add" color={colors.onPrimary} size={22} />
            </Pressable>
          }
        />

        <View style={styles.searchBar}>
          <Ionicons name="search-outline" color={colors.muted} size={18} />
          <Text style={styles.searchText}>Search portfolios</Text>
        </View>

        <View style={styles.list}>
          {portfolios.map((portfolio, index) => {
            const analysis = demoAnalyzePortfolio(portfolio);
            const tone = tones[index % tones.length];

            return (
              <Pressable
                key={portfolio.id}
                onPress={async () => {
                  await setActivePortfolio(portfolio.id);
                  navigation.navigate('PortfolioDetail', { portfolioId: portfolio.id });
                }}
              >
                <Card style={styles.portfolioCard}>
                  <View style={[styles.iconBox, { backgroundColor: tone.bg }]}>
                    <Ionicons name={tone.icon} size={22} color={tone.fg} />
                  </View>

                  <View style={{ flex: 1 }}>
                    <View style={styles.nameRow}>
                      <Text style={styles.name}>{portfolio.name}</Text>
                      {activePortfolioId === portfolio.id ? <Tag label="Active" tone="success" /> : null}
                    </View>
                    <Text style={styles.value}>{hidePortfolioValues ? '••••••' : formatCurrency(portfolio.totalValue)}</Text>
                    <View style={styles.bottomRow}>
                      <Text style={styles.assetCount}>{portfolio.holdings.length} assets</Text>
                      <Text style={[styles.returnText, { color: analysis.annualizedReturn >= 0 ? colors.success : colors.danger }]}>
                        {formatPercent(analysis.annualizedReturn)}
                      </Text>
                    </View>
                  </View>

                  <Ionicons name="chevron-forward" color={colors.muted} size={19} />
                </Card>
              </Pressable>
            );
          })}

          <Pressable onPress={() => navigation.navigate('CreatePortfolio')}>
            <Card style={styles.createCard}>
              <View style={styles.createIcon}>
                <Ionicons name="add" size={24} color={colors.primary} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.createTitle}>Create new portfolio</Text>
                <Text style={styles.createText}>Start building another portfolio</Text>
              </View>
            </Card>
          </Pressable>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 108 },
  addButton: { width: 38, height: 38, borderRadius: 11, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  searchBar: { height: 44, marginTop: spacing.xl, borderRadius: 13, backgroundColor: colors.surfaceAlt, borderWidth: 1, borderColor: colors.borderSoft, flexDirection: 'row', alignItems: 'center', gap: spacing.sm, paddingHorizontal: spacing.md },
  searchText: { color: colors.muted, fontSize: 12 },
  list: { gap: spacing.md, marginTop: spacing.lg },
  portfolioCard: { flexDirection: 'row', gap: spacing.md, alignItems: 'center' },
  iconBox: { width: 52, height: 52, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  nameRow: { flexDirection: 'row', gap: spacing.sm, alignItems: 'center' },
  name: { color: colors.text, fontSize: 16, fontWeight: '900', flexShrink: 1 },
  value: { color: colors.text, fontSize: 18, fontWeight: '900', marginTop: 5 },
  bottomRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 6 },
  assetCount: { color: colors.muted, fontSize: 11 },
  returnText: { fontSize: 11, fontWeight: '900' },
  createCard: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, borderStyle: 'dashed' },
  createIcon: { width: 48, height: 48, borderRadius: 15, borderWidth: 1, borderColor: colors.primary, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.cyanBackground },
  createTitle: { color: colors.text, fontWeight: '900' },
  createText: { color: colors.muted, fontSize: 12, marginTop: 4 }
});
