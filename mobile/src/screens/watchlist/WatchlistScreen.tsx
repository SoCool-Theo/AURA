import { useFocusEffect } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import React, { useCallback, useMemo, useRef, useState } from 'react';
import { MarketDataStatus } from '../../marketData/MarketDataStatus';
import { useMarketDataRefresh } from '../../marketData/useMarketDataRefresh';
import {
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { watchlistApi } from '../../api/watchlistApi';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { ConfirmationDialog } from '../../components/ui/ConfirmationDialog';
import { EmptyState } from '../../components/ui/EmptyState';
import { InlineErrorCard, ScreenErrorState } from '../../components/ui/ErrorState';
import { LoadingState } from '../../components/ui/LoadingState';
import { PageTitle } from '../../components/ui/PageTitle';
import { supportedAssets } from '../../portfolio/supportedAssetSymbols';
import { colors, spacing } from '../../theme/theme';
import type { WatchlistItemResponse } from '../../types/watchlist';
import {
  formatWatchlistDate,
  formatWatchlistPercent,
  formatWatchlistPrice,
  watchlistErrorMessage
} from '../../watchlist/watchlistUi';

export function WatchlistScreen({ navigation }: { navigation: any }) {
  const [items, setItems] = useState<WatchlistItemResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [addingSymbol, setAddingSymbol] = useState<string | null>(null);
  const [removingSymbol, setRemovingSymbol] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [symbolToRemove, setSymbolToRemove] = useState<string | null>(null);
  const read = useRef<AbortController | null>(null);
  const mutation = useRef(false);
  const market = useMarketDataRefresh(() => { if (!mutation.current) setReloadKey(value => value + 1); });

  useFocusEffect(useCallback(() => {
    const controller = new AbortController();
    read.current = controller;
    setLoading(true);
    setRefreshing(true);
    setLoadError(null);
    void watchlistApi.list({ signal: controller.signal })
      .then((response) => { if (!controller.signal.aborted) setItems(response.items); })
      .catch((error) => { if (!controller.signal.aborted) setLoadError(error); })
      .finally(() => { if (!controller.signal.aborted) { setLoading(false); setRefreshing(false); } });
    return () => controller.abort();
  }, [reloadKey]));

  const availableAssets = useMemo(() => {
    const existing = new Set(items.map((item) => item.symbol));
    const normalized = query.trim().toLowerCase();
    return supportedAssets.filter((asset) => !existing.has(asset.symbol) && (
      !normalized
      || asset.symbol.toLowerCase().includes(normalized)
      || asset.name.toLowerCase().includes(normalized)
    ));
  }, [items, query]);

  async function refresh() {
    market.refresh();
  }

  async function add(symbol: string) {
    if (mutation.current) return;
    mutation.current = true;
    read.current?.abort();
    setAddingSymbol(symbol);
    setActionError(null);
    try {
      const added = await watchlistApi.add(symbol);
      setItems((current) => [...current, added]);
      setQuery('');
      setAddOpen(false);
    } catch (error) {
      setActionError(watchlistErrorMessage(error, 'add'));
    } finally {
      mutation.current = false;
      setReloadKey(value => value + 1);
      setAddingSymbol(null);
    }
  }

  async function remove(symbol: string) {
    if (mutation.current) return;
    mutation.current = true;
    read.current?.abort();
    setRemovingSymbol(symbol);
    setActionError(null);
    try {
      await watchlistApi.remove(symbol);
      setItems((current) => current.filter((item) => item.symbol !== symbol));
      setSymbolToRemove(null);
    } catch (error) {
      setActionError(watchlistErrorMessage(error, 'remove'));
    } finally {
      mutation.current = false;
      setReloadKey(value => value + 1);
      setRemovingSymbol(null);
    }
  }

  function confirmRemove(symbol: string) {
    if (removingSymbol) return;
    setActionError(null);
    setSymbolToRemove(symbol);
  }

  if (loading && !items.length) return <LoadingState message="Loading your Watchlist…" />;
  if (loadError && !items.length) {
    return (
      <SafeAreaView style={styles.safe} edges={['bottom']}>
        <ScreenErrorState
          error={loadError}
          resourceName="Watchlist"
          fallbackMessage="Unable to load your Watchlist."
          onRetry={() => setReloadKey((value) => value + 1)}
        />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => void refresh()} tintColor={colors.primary} />}
      >
        <PageTitle
          title="Watchlist"
          subtitle="Latest saved market data for assets you follow."
          right={(
            <Pressable
              accessibilityLabel={addOpen ? 'Close asset picker' : 'Add asset'}
              accessibilityRole="button"
              onPress={() => setAddOpen((value) => !value)}
              style={styles.addButton}
            >
              <Ionicons name={addOpen ? 'close' : 'add'} size={21} color={colors.onPrimary} />
            </Pressable>
          )}
        />

        <MarketDataStatus market={market} symbols={items.map(item => item.symbol)} />
        {actionError ? <View accessibilityRole="alert"><Card style={styles.actionError}><Text style={styles.actionErrorText}>{actionError}</Text></Card></View> : null}
        {loadError && items.length ? (
          <InlineErrorCard
            error={loadError}
            fallbackMessage="Unable to refresh your Watchlist."
            stale
            onRetry={() => void refresh()}
          />
        ) : null}

        {addOpen ? (
          <Card style={styles.pickerCard}>
            <Text style={styles.pickerTitle}>Add a supported asset</Text>
            <Text style={styles.pickerHelp}>Assets already in your Watchlist are hidden.</Text>
            <View style={styles.search}>
              <Ionicons name="search-outline" color={colors.muted} size={17} />
              <TextInput
                accessibilityLabel="Search supported assets"
                autoCapitalize="characters"
                onChangeText={setQuery}
                placeholder="Search symbol or asset name"
                placeholderTextColor={colors.muted}
                style={styles.searchInput}
                value={query}
              />
            </View>
            <ScrollView
              contentContainerStyle={styles.optionsContent}
              keyboardShouldPersistTaps="handled"
              nestedScrollEnabled
              style={styles.options}
            >
              {availableAssets.length ? availableAssets.map((asset) => (
                <Pressable
                  accessibilityLabel={`Add ${asset.symbol}, ${asset.name}`}
                  accessibilityRole="button"
                  accessibilityState={{ disabled: Boolean(addingSymbol) }}
                  disabled={Boolean(addingSymbol)}
                  key={asset.symbol}
                  onPress={() => void add(asset.symbol)}
                  style={({ pressed }) => [styles.option, pressed && styles.pressed]}
                >
                  <View style={{ flex: 1 }}>
                    <Text style={styles.optionSymbol}>{asset.symbol}</Text>
                    <Text numberOfLines={1} style={styles.optionName}>{asset.name}</Text>
                  </View>
                  <Text style={styles.optionAction}>{addingSymbol === asset.symbol ? 'Adding…' : 'Add'}</Text>
                </Pressable>
              )) : <Text style={styles.noOptions}>No matching assets are available to add.</Text>}
            </ScrollView>
          </Card>
        ) : null}

        {!items.length ? (
          <Card style={styles.emptyCard}>
            <EmptyState icon="eye-outline" title="Your Watchlist is empty" description="Add a supported asset to follow its latest saved price and change metrics." />
            <Button title="Add your first asset" onPress={() => setAddOpen(true)} />
          </Card>
        ) : (
          <View style={styles.list}>
            {items.map((item) => {
              const asset = supportedAssets.find((candidate) => candidate.symbol === item.symbol);
              const removing = removingSymbol === item.symbol;
              return (
                <Card key={item.id} style={styles.assetCard}>
                  <View style={styles.assetHeader}>
                    <View style={styles.symbolBadge}><Text style={styles.symbolBadgeText}>{item.symbol.slice(0, 4)}</Text></View>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.symbol}>{item.symbol}</Text>
                      <Text numberOfLines={1} style={styles.assetName}>{asset?.name ?? item.symbol}</Text>
                    </View>
                    <Pressable
                      accessibilityLabel={`Remove ${item.symbol} from Watchlist`}
                      accessibilityRole="button"
                      accessibilityState={{ disabled: removing }}
                      disabled={removing}
                      onPress={() => confirmRemove(item.symbol)}
                      style={styles.removeButton}
                    >
                      <Ionicons name={removing ? 'hourglass-outline' : 'trash-outline'} color={removing ? colors.warning : colors.muted} size={18} />
                    </Pressable>
                  </View>
                  <View style={styles.metrics}>
                    <View style={styles.priceMetric}><Text style={styles.metricLabel}>Latest Price</Text><Text style={styles.price}>{formatWatchlistPrice(item.latest_price)}</Text><Text style={styles.updated}>Updated {formatWatchlistDate(item.latest_price_date)}</Text></View>
                    <View><Text style={styles.metricLabel}>Daily</Text><Text style={[styles.metricValue, item.daily_change_percent !== null && (item.daily_change_percent >= 0 ? styles.positive : styles.negative)]}>{formatWatchlistPercent(item.daily_change_percent)}</Text></View>
                    <View><Text style={styles.metricLabel}>YTD</Text><Text style={[styles.metricValue, item.ytd_change_percent !== null && (item.ytd_change_percent >= 0 ? styles.positive : styles.negative)]}>{formatWatchlistPercent(item.ytd_change_percent)}</Text></View>
                  </View>
                  <Button title="View Outlook" accessibilityLabel={`View ${item.symbol} outlook`} variant="secondary" onPress={() => navigation.navigate('Forecasting', { scope: 'asset', symbol: item.symbol, returnToHome: false })} />
                </Card>
              );
            })}
          </View>
        )}

        <Text style={styles.note}>Prices are latest saved observations, not live quotes. Change metrics come from Aura’s backend.</Text>
      </ScrollView>
      <ConfirmationDialog
        visible={symbolToRemove !== null}
        title={symbolToRemove ? `Remove ${symbolToRemove}?` : 'Remove asset?'}
        description="This removes the asset from your Watchlist. You can add it again later."
        subjectLabel="Watchlist asset"
        subject={symbolToRemove ?? ''}
        confirmLabel="Remove Asset"
        busy={Boolean(symbolToRemove && removingSymbol === symbolToRemove)}
        errorMessage={symbolToRemove ? actionError : null}
        onCancel={() => { if (!removingSymbol) { setSymbolToRemove(null); setActionError(null); } }}
        onConfirm={() => { if (symbolToRemove) void remove(symbolToRemove); }}
      />
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 110 },
  addButton: { width: 44, height: 44, borderRadius: 12, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  actionError: { marginTop: spacing.lg, borderColor: colors.dangerBorder, backgroundColor: colors.negativeBackground },
  actionErrorText: { color: colors.danger, fontSize: 12, lineHeight: 18 },
  pickerCard: { marginTop: spacing.xl },
  pickerTitle: { color: colors.text, fontSize: 16, fontWeight: '900' },
  pickerHelp: { color: colors.muted, fontSize: 11, marginTop: spacing.xs },
  search: { height: 44, marginTop: spacing.md, paddingHorizontal: spacing.md, borderRadius: 13, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surfaceAlt, flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  searchInput: { flex: 1, color: colors.text, fontSize: 12 },
  options: { maxHeight: 280, marginTop: spacing.sm },
  optionsContent: { gap: spacing.xs },
  option: { minHeight: 54, paddingHorizontal: spacing.md, borderRadius: 12, backgroundColor: colors.backgroundSoft, flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  pressed: { opacity: 0.7 },
  optionSymbol: { color: colors.text, fontSize: 13, fontWeight: '900' },
  optionName: { color: colors.muted, fontSize: 10, marginTop: 3 },
  optionAction: { color: colors.primary, fontSize: 11, fontWeight: '900' },
  noOptions: { color: colors.muted, fontSize: 11, lineHeight: 18, textAlign: 'center', padding: spacing.lg },
  emptyCard: { marginTop: spacing.xl },
  list: { gap: spacing.md, marginTop: spacing.xl },
  assetCard: { gap: spacing.md },
  assetHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  symbolBadge: { width: 46, height: 46, borderRadius: 14, backgroundColor: colors.cyanBackground, alignItems: 'center', justifyContent: 'center' },
  symbolBadgeText: { color: colors.primary, fontSize: 11, fontWeight: '900' },
  symbol: { color: colors.text, fontSize: 15, fontWeight: '900' },
  assetName: { color: colors.muted, fontSize: 10, marginTop: 3 },
  removeButton: { width: 42, height: 42, borderRadius: 12, backgroundColor: colors.surfaceAlt, alignItems: 'center', justifyContent: 'center' },
  metrics: { paddingTop: spacing.md, borderTopWidth: 1, borderTopColor: colors.borderSoft, flexDirection: 'row', alignItems: 'flex-start', gap: spacing.lg },
  priceMetric: { flex: 1 },
  metricLabel: { color: colors.muted, fontSize: 9, fontWeight: '800', textTransform: 'uppercase', letterSpacing: 0.6 },
  price: { color: colors.text, fontSize: 18, fontWeight: '900', marginTop: 5 },
  updated: { color: colors.muted, fontSize: 9, marginTop: 4 },
  metricValue: { color: colors.textSecondary, fontSize: 13, fontWeight: '900', marginTop: 7 },
  positive: { color: colors.success },
  negative: { color: colors.danger },
  note: { color: colors.muted, fontSize: 10, lineHeight: 16, textAlign: 'center', marginTop: spacing.xl }
});
