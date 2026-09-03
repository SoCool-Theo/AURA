import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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

import { portfolioErrorMessage } from '../../portfolio/portfolioErrors';
import {
  createHoldingDraft,
  decimalWeightToInput,
  type HoldingDraft,
  validateHoldingDrafts
} from '../../portfolio/portfolioValidation';
import { usePortfolios } from '../../portfolio/usePortfolios';
import { colors, spacing, typography } from '../../theme/theme';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { LoadingState } from '../ui/LoadingState';

type LoadStatus = 'loading' | 'ready' | 'error';

export function HoldingsEditor({
  portfolioId,
  navigation,
  startWithBlankRow = false
}: {
  portfolioId: string;
  navigation: any;
  startWithBlankRow?: boolean;
}) {
  const { getPortfolio, replaceHoldings } = usePortfolios();
  const [portfolioName, setPortfolioName] = useState('Portfolio');
  const [rows, setRows] = useState<HoldingDraft[]>([]);
  const [loadStatus, setLoadStatus] = useState<LoadStatus>('loading');
  const [loadError, setLoadError] = useState<unknown>(null);
  const [saving, setSaving] = useState(false);
  const requestRef = useRef(0);
  const submittingRef = useRef(false);

  const totalPercent = useMemo(() => rows.reduce((total, row) => {
    const value = Number(row.weightPercent);
    return Number.isFinite(value) ? total + value : total;
  }, 0), [rows]);

  const loadPortfolio = useCallback(async () => {
    const requestId = requestRef.current + 1;
    requestRef.current = requestId;
    setLoadStatus('loading');
    setLoadError(null);

    try {
      const portfolio = await getPortfolio(portfolioId);
      if (requestRef.current !== requestId) return;
      const loadedRows = portfolio.holdings.map((holding) => createHoldingDraft(
        holding.symbol,
        decimalWeightToInput(holding.weight)
      ));
      if (startWithBlankRow || !loadedRows.length) {
        loadedRows.push(createHoldingDraft());
      }
      setPortfolioName(portfolio.name);
      setRows(loadedRows);
      setLoadStatus('ready');
    } catch (error) {
      if (requestRef.current !== requestId) return;
      setLoadError(error);
      setLoadStatus('error');
    }
  }, [getPortfolio, portfolioId, startWithBlankRow]);

  useEffect(() => {
    void loadPortfolio();
    return () => {
      requestRef.current += 1;
    };
  }, [loadPortfolio]);

  function patchRow(id: string, patch: Partial<HoldingDraft>) {
    setRows((current) => current.map((row) => (
      row.id === id ? { ...row, ...patch } : row
    )));
  }

  async function save() {
    if (submittingRef.current) return;
    const validation = validateHoldingDrafts(rows);
    if (!validation.holdings) {
      Alert.alert('Check holdings', validation.error);
      return;
    }

    submittingRef.current = true;
    setSaving(true);
    try {
      await replaceHoldings(portfolioId, validation.holdings);
      navigation.goBack();
    } catch (error) {
      Alert.alert('Unable to save holdings', portfolioErrorMessage(error));
    } finally {
      submittingRef.current = false;
      setSaving(false);
    }
  }

  if (loadStatus === 'loading') {
    return <LoadingState message="Loading allocation…" />;
  }

  if (loadStatus === 'error') {
    return (
      <SafeAreaView style={styles.safe} edges={['bottom']}>
        <View style={styles.errorWrap}>
          <Card style={styles.errorCard}>
            <Text style={styles.errorTitle}>Unable to load portfolio</Text>
            <Text style={styles.errorText}>{portfolioErrorMessage(loadError)}</Text>
            <Button title="Retry" onPress={() => void loadPortfolio()} />
          </Card>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
      >
        <Text style={styles.title}>
          {startWithBlankRow ? 'Add holding' : 'Edit holdings'}
        </Text>
        <Text style={styles.subtitle}>
          {portfolioName}: submit the complete ordered allocation. All weights must total 100%.
        </Text>

        <View style={styles.list}>
          {rows.map((row, index) => (
            <Card key={row.id} style={styles.card}>
              <View style={styles.top}>
                <Text style={styles.rowTitle}>HOLDING {index + 1}</Text>
                <Pressable
                  onPress={() => setRows((current) => (
                    current.filter((item) => item.id !== row.id)
                  ))}
                  style={styles.remove}
                  disabled={saving}
                >
                  <Ionicons name="trash-outline" size={18} color={colors.danger} />
                </Pressable>
              </View>

              <View style={styles.fields}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.fieldLabel}>Symbol</Text>
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
                  <Text style={styles.fieldLabel}>Weight %</Text>
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

        <Pressable
          style={styles.addRow}
          onPress={() => setRows((current) => [
            ...current,
            createHoldingDraft()
          ])}
          disabled={saving}
        >
          <Ionicons name="add-circle-outline" size={17} color={colors.primary} />
          <Text style={styles.addRowText}>Add Holding</Text>
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

        <Button
          title={saving ? 'Saving…' : 'Save Complete Allocation'}
          onPress={save}
          disabled={saving}
          style={{ marginTop: spacing.xl }}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 100 },
  title: { color: colors.text, ...typography.h1 },
  subtitle: {
    color: colors.textSecondary,
    marginTop: 6,
    marginBottom: spacing.xl,
    lineHeight: 20
  },
  list: { gap: spacing.md },
  card: { gap: spacing.md },
  top: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  rowTitle: { color: colors.primary, fontSize: 9, fontWeight: '900' },
  remove: {
    width: 40,
    height: 40,
    borderRadius: 13,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.surfaceAlt
  },
  fields: { flexDirection: 'row', gap: spacing.md },
  fieldLabel: {
    color: colors.muted,
    fontSize: 11,
    fontWeight: '800',
    marginBottom: spacing.sm
  },
  input: {
    minHeight: 48,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceAlt,
    color: colors.text,
    paddingHorizontal: spacing.md,
    fontWeight: '800'
  },
  addRow: {
    flexDirection: 'row',
    gap: 7,
    alignItems: 'center',
    marginTop: spacing.md,
    alignSelf: 'flex-start'
  },
  addRowText: { color: colors.primary, fontSize: 11, fontWeight: '900' },
  totalCard: {
    marginTop: spacing.xl,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  totalLabel: { color: colors.muted, fontSize: 9, fontWeight: '900' },
  totalValue: { fontSize: 20, fontWeight: '900' },
  totalValid: { color: colors.success },
  totalInvalid: { color: colors.warning },
  errorWrap: { flex: 1, justifyContent: 'center', padding: spacing.xl },
  errorCard: { gap: spacing.md },
  errorTitle: { color: colors.danger, fontSize: 16, fontWeight: '900' },
  errorText: { color: colors.textSecondary, fontSize: 12, lineHeight: 18 }
});
