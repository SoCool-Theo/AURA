import React, { useMemo, useRef, useState } from 'react';
import {
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { PageTitle } from '../../components/ui/PageTitle';
import {
  PortfolioCreatedWithoutHoldingsError,
  portfolioErrorMessage
} from '../../portfolio/portfolioErrors';
import {
  createHoldingDraft,
  type HoldingDraft,
  validateHoldingDrafts
} from '../../portfolio/portfolioValidation';
import { usePortfolios } from '../../portfolio/usePortfolios';
import { colors, spacing } from '../../theme/theme';

export function CreatePortfolioScreen({ navigation }: { navigation: any }) {
  const { createPortfolioWithHoldings } = usePortfolios();
  const [name, setName] = useState('');
  const [rows, setRows] = useState<HoldingDraft[]>([createHoldingDraft()]);
  const [saving, setSaving] = useState(false);
  const submittingRef = useRef(false);

  const totalPercent = useMemo(() => rows.reduce((total, row) => {
    const value = Number(row.weightPercent);
    return Number.isFinite(value) ? total + value : total;
  }, 0), [rows]);

  function patchRow(id: string, patch: Partial<HoldingDraft>) {
    setRows((current) => current.map((row) => (
      row.id === id ? { ...row, ...patch } : row
    )));
  }

  function addRow() {
    setRows((current) => [...current, createHoldingDraft()]);
  }

  async function save() {
    if (submittingRef.current) return;
    const normalizedName = name.trim();
    if (!normalizedName) {
      Alert.alert('Portfolio name required', 'Enter a portfolio name.');
      return;
    }

    const validation = validateHoldingDrafts(rows);
    if (!validation.holdings) {
      Alert.alert('Check holdings', validation.error);
      return;
    }

    submittingRef.current = true;
    setSaving(true);
    try {
      const portfolio = await createPortfolioWithHoldings(
        normalizedName,
        validation.holdings
      );
      navigation.replace('PortfolioDetail', { portfolioId: portfolio.id });
    } catch (error) {
      if (error instanceof PortfolioCreatedWithoutHoldingsError) {
        Alert.alert(
          'Portfolio created without holdings',
          `${error.message} ${portfolioErrorMessage(error.causeValue)}`,
          [{
            text: 'View portfolio',
            onPress: () => navigation.replace('PortfolioDetail', {
              portfolioId: error.portfolio.id
            })
          }]
        );
      } else {
        Alert.alert(
          'Unable to create portfolio',
          portfolioErrorMessage(error)
        );
      }
    } finally {
      submittingRef.current = false;
      setSaving(false);
    }
  }

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
      >
        <PageTitle
          title="Create New Portfolio"
          subtitle="Enter symbols and percentage weights. The complete allocation must equal 100%."
        />

        <Card style={styles.formCard}>
          <Input
            label="Portfolio Name"
            value={name}
            onChangeText={setName}
            autoCapitalize="words"
            editable={!saving}
          />
        </Card>

        <View style={styles.sectionHeader}>
          <View style={{ flex: 1 }}>
            <Text style={styles.sectionTitle}>Holdings</Text>
            <Text style={styles.sectionText}>
              Symbols are entered manually; no asset search is available.
            </Text>
          </View>
          <Pressable style={styles.addButton} onPress={addRow} disabled={saving}>
            <Ionicons name="add" size={17} color={colors.onPrimary} />
          </Pressable>
        </View>

        <View style={styles.rows}>
          {rows.map((row, index) => (
            <Card key={row.id} style={styles.assetCard}>
              <View style={styles.assetHeader}>
                <Text style={styles.assetNumber}>HOLDING {index + 1}</Text>
                <Pressable
                  onPress={() => setRows((current) => (
                    current.filter((item) => item.id !== row.id)
                  ))}
                  disabled={saving}
                >
                  <Ionicons name="trash-outline" size={18} color={colors.danger} />
                </Pressable>
              </View>

              <View style={styles.inline}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.label}>Symbol</Text>
                  <TextInput
                    value={row.symbol}
                    onChangeText={(value) => patchRow(row.id, {
                      symbol: value.toUpperCase()
                    })}
                    autoCapitalize="characters"
                    placeholder="AAPL"
                    placeholderTextColor={colors.muted}
                    style={styles.input}
                    editable={!saving}
                  />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.label}>Weight %</Text>
                  <TextInput
                    value={row.weightPercent}
                    onChangeText={(value) => patchRow(row.id, {
                      weightPercent: value
                    })}
                    keyboardType="decimal-pad"
                    placeholder="0"
                    placeholderTextColor={colors.muted}
                    style={styles.input}
                    editable={!saving}
                  />
                </View>
              </View>
            </Card>
          ))}
        </View>

        <Pressable style={styles.textButton} onPress={addRow} disabled={saving}>
          <Ionicons name="add-circle-outline" size={17} color={colors.primary} />
          <Text style={styles.textButtonLabel}>Add Holding</Text>
        </Pressable>

        <Card style={styles.totalCard}>
          <Text style={styles.totalLabel}>TOTAL ALLOCATION</Text>
          <Text style={[
            styles.totalValue,
            Math.abs(totalPercent - 100) <= 1e-7
              ? styles.totalValid
              : styles.totalInvalid
          ]}>
            {totalPercent.toFixed(2)}%
          </Text>
        </Card>

        <View style={styles.footerActions}>
          <Button
            title="Cancel"
            variant="secondary"
            style={{ flex: 1 }}
            onPress={() => navigation.goBack()}
            disabled={saving}
          />
          <Button
            title={saving ? 'Creating…' : 'Create Portfolio'}
            style={{ flex: 1.35 }}
            onPress={save}
            disabled={saving}
          />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 100 },
  formCard: { marginTop: spacing.xl },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: spacing.md,
    marginTop: spacing.xl,
    marginBottom: spacing.md
  },
  sectionTitle: { color: colors.text, fontSize: 18, fontWeight: '900' },
  sectionText: { color: colors.muted, fontSize: 10, marginTop: 3 },
  addButton: {
    width: 36,
    height: 36,
    borderRadius: 11,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center'
  },
  rows: { gap: spacing.md },
  assetCard: { gap: spacing.md },
  assetHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  assetNumber: {
    color: colors.primary,
    fontSize: 9,
    fontWeight: '900',
    letterSpacing: 1
  },
  inline: { flexDirection: 'row', gap: spacing.md },
  label: {
    color: colors.textSecondary,
    fontSize: 10,
    fontWeight: '800',
    marginBottom: 6
  },
  input: {
    minHeight: 44,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceAlt,
    color: colors.text,
    paddingHorizontal: spacing.md,
    fontSize: 12,
    fontWeight: '700'
  },
  textButton: {
    flexDirection: 'row',
    gap: 7,
    alignItems: 'center',
    marginTop: spacing.md,
    alignSelf: 'flex-start'
  },
  textButtonLabel: { color: colors.primary, fontSize: 11, fontWeight: '900' },
  totalCard: {
    marginTop: spacing.xl,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  totalLabel: {
    color: colors.muted,
    fontSize: 9,
    fontWeight: '900',
    letterSpacing: 0.9
  },
  totalValue: { fontSize: 20, fontWeight: '900' },
  totalValid: { color: colors.success },
  totalInvalid: { color: colors.warning },
  footerActions: { flexDirection: 'row', gap: spacing.md, marginTop: spacing.xl }
});
