import React, { useMemo, useState } from 'react';
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
import { Ionicons } from '@expo/vector-icons';

import { PortfolioCard } from '../../components/portfolio/PortfolioCard';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { LoadingState } from '../../components/ui/LoadingState';
import { PageTitle } from '../../components/ui/PageTitle';
import { portfolioErrorMessage } from '../../portfolio/portfolioErrors';
import { usePortfolios } from '../../portfolio/usePortfolios';
import { colors, spacing } from '../../theme/theme';

export function PortfoliosScreen({ navigation }: { navigation: any }) {
  const {
    portfolios,
    activePortfolioId,
    listStatus,
    listError,
    isRefreshing,
    refreshPortfolios,
    selectPortfolio
  } = usePortfolios();
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) return portfolios;
    return portfolios.filter((portfolio) => (
      portfolio.name.toLowerCase().includes(normalizedQuery)
    ));
  }, [portfolios, query]);

  if (
    (listStatus === 'idle' || listStatus === 'loading')
    && !portfolios.length
  ) {
    return <LoadingState message="Loading portfolios…" />;
  }

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        refreshControl={(
          <RefreshControl
            refreshing={isRefreshing}
            onRefresh={() => void refreshPortfolios()}
            tintColor={colors.primary}
          />
        )}
      >
        <PageTitle
          title="My Portfolios"
          subtitle="Create and manage your saved portfolio allocations."
          right={(
            <Pressable
              style={styles.newButton}
              onPress={() => navigation.navigate('CreatePortfolio')}
            >
              <Ionicons name="add" size={19} color={colors.onPrimary} />
            </Pressable>
          )}
        />

        {listStatus === 'error' ? (
          <Card style={styles.errorCard}>
            <Text style={styles.errorTitle}>Unable to load portfolios</Text>
            <Text style={styles.errorText}>
              {portfolioErrorMessage(listError)}
            </Text>
            <Button title="Retry" onPress={() => void refreshPortfolios()} />
          </Card>
        ) : null}

        {portfolios.length ? (
          <View style={styles.searchBar}>
            <Ionicons name="search-outline" size={17} color={colors.muted} />
            <TextInput
              value={query}
              onChangeText={setQuery}
              placeholder="Search portfolios"
              placeholderTextColor={colors.muted}
              style={styles.searchInput}
            />
          </View>
        ) : null}

        {listStatus !== 'error' && !portfolios.length ? (
          <Card style={styles.emptyCard}>
            <EmptyState
              title="No portfolios yet"
              description="Create your first portfolio and add a complete symbol-and-weight allocation."
            />
          </Card>
        ) : filtered.length ? (
          <View style={styles.list}>
            {filtered.map((portfolio) => (
              <PortfolioCard
                key={portfolio.id}
                portfolio={portfolio}
                active={portfolio.id === activePortfolioId}
                onPress={() => {
                  selectPortfolio(portfolio.id);
                  navigation.navigate('PortfolioDetail', {
                    portfolioId: portfolio.id
                  });
                }}
              />
            ))}
          </View>
        ) : portfolios.length ? (
          <Card style={styles.emptyCard}>
            <EmptyState
              icon="search-outline"
              title="No matching portfolios"
              description="Try a different portfolio name."
            />
          </Card>
        ) : null}

        <Pressable onPress={() => navigation.navigate('CreatePortfolio')}>
          <Card style={styles.createCta}>
            <View style={{ flex: 1 }}>
              <Text style={styles.ctaEyebrow}>CREATE NEW PORTFOLIO</Text>
              <Text style={styles.ctaTitle}>
                Build an ordered allocation using symbols and percentage weights.
              </Text>
              <View style={styles.ctaLink}>
                <Ionicons name="add-circle-outline" size={16} color={colors.primary} />
                <Text style={styles.ctaLinkText}>Create Portfolio</Text>
              </View>
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
  newButton: {
    width: 40,
    height: 40,
    borderRadius: 12,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center'
  },
  errorCard: { gap: spacing.md, marginTop: spacing.xl },
  errorTitle: { color: colors.danger, fontSize: 15, fontWeight: '900' },
  errorText: { color: colors.textSecondary, fontSize: 12, lineHeight: 18 },
  searchBar: {
    height: 44,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    borderRadius: 13,
    backgroundColor: colors.surfaceAlt,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    marginTop: spacing.xl
  },
  searchInput: { flex: 1, color: colors.text, fontSize: 12 },
  list: { gap: spacing.md, marginTop: spacing.xl },
  emptyCard: { marginTop: spacing.xl },
  createCta: {
    marginTop: spacing.xl,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xl,
    borderStyle: 'dashed',
    borderColor: colors.primary
  },
  ctaEyebrow: {
    color: colors.primary,
    fontSize: 9,
    fontWeight: '900',
    letterSpacing: 1
  },
  ctaTitle: {
    color: colors.text,
    fontSize: 17,
    fontWeight: '900',
    lineHeight: 22,
    marginTop: 6
  },
  ctaLink: {
    flexDirection: 'row',
    gap: 6,
    alignItems: 'center',
    marginTop: spacing.md
  },
  ctaLinkText: { color: colors.primary, fontSize: 11, fontWeight: '900' }
});
