import React, { useEffect, useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { EmptyState } from '../../components/ui/EmptyState';
import { useAppData } from '../../hooks/useAppData';
import type { DemoHolding as Holding } from '../../types/demo';
import { colors, spacing, typography } from '../../theme/theme';

export function EditHoldingsScreen({ route, navigation }: { route: any; navigation: any }) {
  const { portfolios, replaceHoldings } = useAppData();
  const portfolio = portfolios.find((item) => item.id === route.params.portfolioId);
  const [holdings, setHoldings] = useState<Holding[]>(portfolio?.holdings ?? []);

  useEffect(() => {
    if (portfolio) setHoldings(portfolio.holdings.map((item) => ({ ...item })));
  }, [portfolio?.id]);

  if (!portfolio) {
    return <SafeAreaView style={styles.safe}><EmptyState title="Portfolio not found" description="Return to Portfolios." /></SafeAreaView>;
  }

  const selectedPortfolioId = portfolio.id;

  async function save() {
    if (holdings.some((item) => !Number.isFinite(item.value) || item.value < 0)) {
      Alert.alert('Invalid amount', 'All invested amounts must be zero or greater.');
      return;
    }
    await replaceHoldings(selectedPortfolioId, holdings);
    navigation.goBack();
  }

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Text style={styles.title}>Edit holdings</Text>
        <Text style={styles.subtitle}>Change invested amounts or remove assets. Weights update when you save.</Text>

        {holdings.length ? (
          <View style={styles.list}>
            {holdings.map((holding, index) => (
              <Card key={holding.symbol} style={styles.card}>
                <View style={styles.top}>
                  <View>
                    <Text style={styles.symbol}>{holding.symbol}</Text>
                    <Text style={styles.name}>{holding.name}</Text>
                  </View>
                  <Pressable
                    onPress={() => setHoldings((items) => items.filter((_, i) => i !== index))}
                    style={styles.remove}
                  >
                    <Ionicons name="trash-outline" size={18} color={colors.danger} />
                  </Pressable>
                </View>
                <Text style={styles.fieldLabel}>Amount invested</Text>
                <TextInput
                  value={String(holding.value)}
                  onChangeText={(text) => {
                    const value = Number(text || 0);
                    setHoldings((items) => items.map((item, i) => i === index ? { ...item, value } : item));
                  }}
                  keyboardType="decimal-pad"
                  style={styles.input}
                  placeholderTextColor={colors.muted}
                />
              </Card>
            ))}
          </View>
        ) : (
          <Card><EmptyState title="No holdings" description="Go back and add an asset first." /></Card>
        )}

        <Button title="Save holdings" onPress={save} style={{ marginTop: spacing.xl }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 100 },
  title: { color: colors.text, ...typography.h1 },
  subtitle: { color: colors.textSecondary, marginTop: 6, marginBottom: spacing.xl, lineHeight: 20 },
  list: { gap: spacing.md },
  card: { gap: spacing.md },
  top: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  symbol: { color: colors.primary, fontWeight: '900', fontSize: 17 },
  name: { color: colors.textSecondary, marginTop: 3 },
  remove: { width: 40, height: 40, borderRadius: 13, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surfaceAlt },
  fieldLabel: { color: colors.muted, fontSize: 11, fontWeight: '800' },
  input: { minHeight: 48, borderRadius: 14, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surfaceAlt, color: colors.text, paddingHorizontal: spacing.md, fontWeight: '800' }
});
