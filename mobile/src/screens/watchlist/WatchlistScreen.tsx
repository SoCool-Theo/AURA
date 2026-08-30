import React, { useMemo, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { PageTitle } from '../../components/ui/PageTitle';
import { Tag } from '../../components/ui/Tag';
import { useAppData } from '../../hooks/useAppData';
import { watchlistCatalog } from '../../mocks/watchlist.mock';
import type { WatchlistItem } from '../../types/watchlist';
import { colors, spacing } from '../../theme/theme';
import { formatCurrency } from '../../utils/formatting';

export function WatchlistScreen() {
  const { watchlistSymbols, addWatchlistSymbol, removeWatchlistSymbol } = useAppData();
  const [query, setQuery] = useState('');

  const watched = watchlistSymbols
    .map((symbol) => watchlistCatalog.find((item) => item.symbol === symbol))
    .filter((item): item is WatchlistItem => Boolean(item));

  const results = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return [];
    return watchlistCatalog
      .filter(
        (item) =>
          item.symbol.toLowerCase().includes(normalized) ||
          item.name.toLowerCase().includes(normalized)
      )
      .slice(0, 6);
  }, [query]);

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <PageTitle
          title="Watchlist"
          subtitle="Keep selected assets close for quick market monitoring."
          right={
            <View style={styles.plusButton}>
              <Ionicons name="add" color={colors.text} size={21} />
            </View>
          }
        />

        <Input
          value={query}
          onChangeText={setQuery}
          placeholder="Search assets"
          autoCapitalize="characters"
        />

        {results.length ? (
          <Card style={styles.resultsCard}>
            {results.map((item) => {
              const added = watchlistSymbols.includes(item.symbol);
              return (
                <Pressable
                  key={item.symbol}
                  style={styles.searchResult}
                  onPress={async () => {
                    if (!added) await addWatchlistSymbol(item.symbol);
                    setQuery('');
                  }}
                >
                  <View>
                    <Text style={styles.resultSymbol}>{item.symbol}</Text>
                    <Text style={styles.resultName}>{item.name}</Text>
                  </View>
                  <Ionicons
                    name={added ? 'checkmark-circle' : 'add-circle-outline'}
                    color={added ? colors.success : colors.primary}
                    size={23}
                  />
                </Pressable>
              );
            })}
          </Card>
        ) : null}

        <View style={styles.filters}>
          <Tag label="All" tone="primary" />
          <Tag label="Stocks" />
          <Tag label="ETFs" />
          <Tag label="Crypto" />
        </View>

        <View style={styles.list}>
          {watched.map((item) => (
            <Card key={item.symbol} style={styles.assetCard}>
              <View style={styles.assetTop}>
                <View style={styles.logo}>
                  <Text style={styles.logoText}>{item.symbol.slice(0, 1)}</Text>
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.symbol}>{item.symbol}</Text>
                  <Text style={styles.name}>{item.name}</Text>
                </View>
                <Pressable onPress={() => removeWatchlistSymbol(item.symbol)}>
                  <Ionicons name="close" size={18} color={colors.muted} />
                </Pressable>
              </View>

              <View style={styles.priceRow}>
                <Text style={styles.price}>{formatCurrency(item.price)}</Text>
                <View style={styles.changeBox}>
                  <Ionicons
                    name={item.changePercent >= 0 ? 'trending-up' : 'trending-down'}
                    size={14}
                    color={item.changePercent >= 0 ? colors.success : colors.danger}
                  />
                  <Text
                    style={[
                      styles.change,
                      { color: item.changePercent >= 0 ? colors.success : colors.danger }
                    ]}
                  >
                    {item.changePercent > 0 ? '+' : ''}
                    {item.changePercent.toFixed(2)}%
                  </Text>
                </View>
              </View>

              <View style={styles.sparkline}>
                {[12, 20, 17, 28, 24, 36, 32, 43, 39, 48].map((height, index) => (
                  <View
                    key={index}
                    style={[
                      styles.sparkBar,
                      {
                        height,
                        backgroundColor:
                          item.changePercent >= 0 ? colors.primary : colors.danger
                      }
                    ]}
                  />
                ))}
              </View>
            </Card>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 100, gap: spacing.md },
  plusButton: { width: 38, height: 38, borderRadius: 12, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, alignItems: 'center', justifyContent: 'center' },
  resultsCard: { gap: spacing.sm },
  searchResult: { minHeight: 50, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderBottomWidth: 1, borderBottomColor: colors.borderSoft },
  resultSymbol: { color: colors.text, fontWeight: '900' },
  resultName: { color: colors.muted, fontSize: 11, marginTop: 3 },
  filters: { flexDirection: 'row', gap: spacing.sm, marginVertical: spacing.sm },
  list: { gap: spacing.md },
  assetCard: { gap: spacing.md },
  assetTop: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  logo: { width: 42, height: 42, borderRadius: 13, backgroundColor: colors.surfaceAlt, alignItems: 'center', justifyContent: 'center' },
  logoText: { color: colors.text, fontSize: 17, fontWeight: '900' },
  symbol: { color: colors.text, fontSize: 15, fontWeight: '900' },
  name: { color: colors.muted, fontSize: 11, marginTop: 3 },
  priceRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  price: { color: colors.text, fontSize: 21, fontWeight: '900' },
  changeBox: { flexDirection: 'row', gap: 5, alignItems: 'center' },
  change: { fontSize: 12, fontWeight: '900' },
  sparkline: { height: 50, flexDirection: 'row', alignItems: 'flex-end', gap: 5 },
  sparkBar: { width: 5, borderRadius: 3, opacity: 0.8 }
});
