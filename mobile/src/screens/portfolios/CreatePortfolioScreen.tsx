import React, { useMemo, useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { PageTitle } from '../../components/ui/PageTitle';
import { useAppData } from '../../hooks/useAppData';
import { colors, spacing } from '../../theme/theme';
import type { DemoHolding as Holding } from '../../types/demo';
import { formatCurrency } from '../../utils/formatting';

type DraftHolding = Omit<Holding, 'weight'> & { id: string };

const starter: DraftHolding[] = [
  { id: '1', symbol: 'AAPL', name: 'Apple Inc.', value: 4000, risk: 'Medium' },
  { id: '2', symbol: 'NVDA', name: 'NVIDIA Corp.', value: 3000, risk: 'High' },
  { id: '3', symbol: 'SPY', name: 'SPDR S&P 500 ETF', value: 3000, risk: 'Low' }
];

export function CreatePortfolioScreen({ navigation }: { navigation: any }) {
  const { createPortfolioWithHoldings } = useAppData();
  const [name, setName] = useState('My New Portfolio');
  const [rows, setRows] = useState<DraftHolding[]>(starter);
  const [saving, setSaving] = useState(false);

  const totalAmount = useMemo(() => rows.reduce((sum, row) => sum + Number(row.value || 0), 0), [rows]);
  const allocationFor = (value: number) => totalAmount > 0 ? (value / totalAmount) * 100 : 0;

  function patchRow(id: string, patch: Partial<DraftHolding>) {
    setRows((current) => current.map((row) => row.id === id ? { ...row, ...patch } : row));
  }

  function addRow() {
    setRows((current) => [
      ...current,
      { id: String(Date.now()), symbol: '', name: '', value: 0, risk: 'Medium' }
    ]);
  }

  async function save() {
    if (!name.trim()) {
      Alert.alert('Portfolio name required', 'Enter a portfolio name.');
      return;
    }
    if (!rows.length || rows.some((row) => !row.symbol.trim() || !row.name.trim() || row.value <= 0)) {
      Alert.alert('Check holdings', 'Each asset needs a symbol, name, and positive invested amount.');
      return;
    }

    try {
      setSaving(true);
      const portfolio = await createPortfolioWithHoldings(
        name.trim(),
        rows.map((row) => ({
          symbol: row.symbol.trim().toUpperCase(),
          name: row.name.trim(),
          value: Number(row.value),
          weight: 0,
          risk: row.risk
        }))
      );
      navigation.replace('PortfolioDetail', { portfolioId: portfolio.id });
    } finally {
      setSaving(false);
    }
  }

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <PageTitle title="Create New Portfolio" subtitle="Add assets and set your investment amounts. Aura calculates portfolio weights automatically." />

        <Card style={styles.formCard}>
          <Input label="Portfolio Name" value={name} onChangeText={setName} autoCapitalize="words" />
        </Card>

        <View style={styles.sectionHeader}>
          <View>
            <Text style={styles.sectionTitle}>Holdings</Text>
            <Text style={styles.sectionText}>Add the assets that belong to this portfolio.</Text>
          </View>
          <Pressable style={styles.addButton} onPress={addRow}>
            <Ionicons name="add" size={17} color={colors.onPrimary} />
          </Pressable>
        </View>

        <View style={styles.rows}>
          {rows.map((row, index) => (
            <Card key={row.id} style={styles.assetCard}>
              <View style={styles.assetHeader}>
                <Text style={styles.assetNumber}>ASSET {index + 1}</Text>
                <Pressable onPress={() => setRows((current) => current.filter((item) => item.id !== row.id))}>
                  <Ionicons name="trash-outline" size={18} color={colors.danger} />
                </Pressable>
              </View>

              <View style={styles.inline}>
                <View style={{ flex: 0.7 }}>
                  <Text style={styles.label}>Symbol</Text>
                  <TextInput value={row.symbol} onChangeText={(value) => patchRow(row.id, { symbol: value.toUpperCase() })} autoCapitalize="characters" placeholder="AAPL" placeholderTextColor={colors.muted} style={styles.input} />
                </View>
                <View style={{ flex: 1.3 }}>
                  <Text style={styles.label}>Asset Name</Text>
                  <TextInput value={row.name} onChangeText={(value) => patchRow(row.id, { name: value })} placeholder="Apple Inc." placeholderTextColor={colors.muted} style={styles.input} />
                </View>
              </View>

              <View style={styles.inline}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.label}>Amount (USD)</Text>
                  <TextInput value={String(row.value)} onChangeText={(value) => patchRow(row.id, { value: Number(value || 0) })} keyboardType="decimal-pad" placeholder="0" placeholderTextColor={colors.muted} style={styles.input} />
                </View>
                <View style={styles.allocationBox}>
                  <Text style={styles.label}>Allocation</Text>
                  <Text style={styles.allocationValue}>{allocationFor(row.value).toFixed(1)}%</Text>
                </View>
              </View>

              <Text style={styles.label}>Demo Risk Profile</Text>
              <View style={styles.riskRow}>
                {(['Low', 'Medium', 'High'] as const).map((risk) => {
                  const active = row.risk === risk;
                  return (
                    <Pressable key={risk} onPress={() => patchRow(row.id, { risk })} style={[styles.riskChip, active && styles.riskChipActive]}>
                      <Text style={[styles.riskText, active && styles.riskTextActive]}>{risk}</Text>
                    </Pressable>
                  );
                })}
              </View>
            </Card>
          ))}
        </View>

        <Pressable style={styles.textButton} onPress={addRow}>
          <Ionicons name="add-circle-outline" size={17} color={colors.primary} />
          <Text style={styles.textButtonLabel}>Add Asset</Text>
        </Pressable>

        <Card style={styles.totalCard}>
          <View>
            <Text style={styles.totalLabel}>TOTAL ALLOCATION</Text>
            <Text style={styles.totalValue}>{totalAmount > 0 ? '100.0%' : '0.0%'}</Text>
          </View>
          <View style={styles.totalRight}>
            <Text style={styles.totalLabel}>TOTAL AMOUNT</Text>
            <Text style={styles.totalAmount}>{formatCurrency(totalAmount)}</Text>
          </View>
        </Card>

        <View style={styles.footerActions}>
          <Button title="Cancel" variant="secondary" style={{ flex: 1 }} onPress={() => navigation.goBack()} />
          <Button title={saving ? 'Creating…' : 'Create Portfolio'} style={{ flex: 1.35 }} onPress={save} disabled={saving} />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 100 },
  formCard: { marginTop: spacing.xl },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: spacing.xl, marginBottom: spacing.md },
  sectionTitle: { color: colors.text, fontSize: 18, fontWeight: '900' },
  sectionText: { color: colors.muted, fontSize: 10, marginTop: 3 },
  addButton: { width: 36, height: 36, borderRadius: 11, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  rows: { gap: spacing.md },
  assetCard: { gap: spacing.md },
  assetHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  assetNumber: { color: colors.primary, fontSize: 9, fontWeight: '900', letterSpacing: 1 },
  inline: { flexDirection: 'row', gap: spacing.md },
  label: { color: colors.textSecondary, fontSize: 10, fontWeight: '800', marginBottom: 6 },
  input: { minHeight: 44, borderRadius: 12, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surfaceAlt, color: colors.text, paddingHorizontal: spacing.md, fontSize: 12, fontWeight: '700' },
  allocationBox: { width: 92, justifyContent: 'flex-end' },
  allocationValue: { color: colors.primary, fontSize: 18, fontWeight: '900', minHeight: 44, textAlignVertical: 'center' },
  riskRow: { flexDirection: 'row', gap: spacing.sm },
  riskChip: { flex: 1, minHeight: 38, borderRadius: 11, borderWidth: 1, borderColor: colors.borderSoft, backgroundColor: colors.surfaceAlt, alignItems: 'center', justifyContent: 'center' },
  riskChipActive: { borderColor: colors.primary, backgroundColor: colors.selectedBackground },
  riskText: { color: colors.textSecondary, fontSize: 10, fontWeight: '800' },
  riskTextActive: { color: colors.primary },
  textButton: { flexDirection: 'row', gap: 7, alignItems: 'center', marginTop: spacing.md, alignSelf: 'flex-start' },
  textButtonLabel: { color: colors.primary, fontSize: 11, fontWeight: '900' },
  totalCard: { marginTop: spacing.xl, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  totalLabel: { color: colors.muted, fontSize: 9, fontWeight: '900', letterSpacing: 0.9 },
  totalValue: { color: colors.success, fontSize: 20, fontWeight: '900', marginTop: 5 },
  totalRight: { alignItems: 'flex-end' },
  totalAmount: { color: colors.text, fontSize: 20, fontWeight: '900', marginTop: 5 },
  footerActions: { flexDirection: 'row', gap: spacing.md, marginTop: spacing.xl }
});
