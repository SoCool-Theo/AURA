import React, { useRef, useState } from 'react';
import {
  Pressable,
  StyleSheet,
  Text,
  View
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import { apiValidationIssues } from '../../api/apiErrorPresentation';
import { AssetSymbolField } from '../../components/portfolio/AssetSymbolField';
import { HoldingDecimalInput } from '../../components/portfolio/HoldingDecimalInput';
import { PurchaseDateField } from '../../components/portfolio/PurchaseDateField';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { FormErrorSummary } from '../../components/ui/ErrorState';
import { Input } from '../../components/ui/Input';
import { KeyboardAwareScrollView } from '../../components/ui/KeyboardAwareScrollView';
import { PageTitle } from '../../components/ui/PageTitle';
import {
  PortfolioCreatedWithoutHoldingsError,
  portfolioErrorMessage
} from '../../portfolio/portfolioErrors';
import {
  createPlannedHoldingDraft,
  createRealHoldingDraft,
  type PlannedHoldingDraft,
  type RealHoldingDraft,
  validatePlannedHoldingDrafts,
  validateRealHoldingDrafts
} from '../../portfolio/portfolioValidation';
import { usePortfolios } from '../../portfolio/usePortfolios';
import { colors, spacing } from '../../theme/theme';
import type {
  PortfolioCurrency,
  PortfolioPlannedHoldingInput,
  PortfolioRealHoldingInput
} from '../../types/portfolio';

type CreateMode = 'CURRENT' | 'PLANNED';
type HoldingDraft = RealHoldingDraft | PlannedHoldingDraft;

export function CreatePortfolioScreen({ navigation }: { navigation: any }) {
  const { createPortfolioWithPlannedHoldings, createPortfolioWithRealHoldings } = usePortfolios();
  const [name, setName] = useState('');
  const [mode, setMode] = useState<CreateMode>('CURRENT');
  const [planCurrency, setPlanCurrency] = useState<PortfolioCurrency>('USD');
  const [rows, setRows] = useState<HoldingDraft[]>([
    createRealHoldingDraft()
  ]);
  const [saving, setSaving] = useState(false);
  const [submitError, setSubmitError] = useState<unknown>(null);
  const [submitMessage, setSubmitMessage] = useState<string | null>(null);
  const [partialPortfolioId, setPartialPortfolioId] = useState<string | null>(null);
  const submittingRef = useRef(false);

  function clearFormError() {
    setSubmitError(null);
    setSubmitMessage(null);
    setPartialPortfolioId(null);
  }

  function patchRow(id: string, patch: Partial<HoldingDraft>) {
    clearFormError();
    setRows((current) => current.map((row) => (
      row.id === id ? { ...row, ...patch } : row
    )));
  }

  function addRow() {
    setRows((current) => [
      ...current,
      mode === 'PLANNED' ? createPlannedHoldingDraft() : createRealHoldingDraft()
    ]);
  }

  function selectMode(nextMode: CreateMode) {
    if (nextMode === mode || saving) return;
    clearFormError();
    setMode(nextMode);
    setRows([nextMode === 'PLANNED' ? createPlannedHoldingDraft() : createRealHoldingDraft()]);
  }

  function moveRow(index: number, offset: -1 | 1) {
    setRows((current) => {
      const destination = index + offset;
      if (destination < 0 || destination >= current.length) return current;
      const next = [...current];
      [next[index], next[destination]] = [next[destination], next[index]];
      return next;
    });
  }

  async function save() {
    if (submittingRef.current) return;
    const normalizedName = name.trim();
    if (!normalizedName) {
      setSubmitError(null);
      setSubmitMessage('Enter a portfolio name.');
      return;
    }

    const validation = mode === 'PLANNED'
      ? validatePlannedHoldingDrafts(rows as PlannedHoldingDraft[])
      : validateRealHoldingDrafts(rows as RealHoldingDraft[]);
    if (!validation.holdings) {
      setSubmitError(null);
      setSubmitMessage(validation.error);
      return;
    }

    submittingRef.current = true;
    setSaving(true);
    clearFormError();
    try {
      const portfolio = mode === 'PLANNED'
        ? await createPortfolioWithPlannedHoldings(
          normalizedName,
          planCurrency,
          validation.holdings as PortfolioPlannedHoldingInput[]
        )
        : await createPortfolioWithRealHoldings(
          normalizedName,
          validation.holdings as PortfolioRealHoldingInput[]
        );
      navigation.replace('PortfolioDetail', { portfolioId: portfolio.id });
    } catch (error) {
      if (error instanceof PortfolioCreatedWithoutHoldingsError) {
        setSubmitError(error.causeValue);
        setSubmitMessage(`${error.message} ${portfolioErrorMessage(error.causeValue)}`);
        setPartialPortfolioId(error.portfolio.id);
      } else {
        setSubmitError(error);
        setSubmitMessage(portfolioErrorMessage(error));
      }
    } finally {
      submittingRef.current = false;
      setSaving(false);
    }
  }

  const validationIssues = apiValidationIssues(submitError);
  const fieldIssue = (index: number, field: string) => validationIssues.find(
    (issue) => issue.path.endsWith(`holdings.${index}.${field}`)
  )?.message;
  const nameError = validationIssues.find((issue) => issue.path.endsWith('name'))?.message;

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <KeyboardAwareScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
      >
        <PageTitle
          title="Create New Portfolio"
          subtitle={mode === 'PLANNED'
            ? 'Model a proposed investment. Aura derives target allocation from your amounts.'
            : 'Record what you own. Aura values your shares and calculates current allocation automatically.'}
        />

        <Card style={styles.formCard}>
          <Input
            label="Portfolio Name"
            value={name}
            onChangeText={(value) => {
              clearFormError();
              setName(value);
            }}
            autoCapitalize="words"
            editable={!saving}
            error={nameError}
          />
        </Card>

        <Card style={styles.modeCard}>
          <Text style={styles.label}>WHAT WOULD YOU LIKE TO ANALYZE?</Text>
          <View style={styles.modeControl}>
            {([
              ['CURRENT', 'My Current Portfolio'],
              ['PLANNED', 'A Planned Portfolio']
            ] as const).map(([value, label]) => {
              const selected = mode === value;
              return (
                <Pressable
                  key={value}
                  accessibilityLabel={label}
                  accessibilityRole="radio"
                  accessibilityState={{ selected, disabled: saving }}
                  disabled={saving}
                  onPress={() => selectMode(value)}
                  style={[styles.modeOption, selected && styles.modeOptionSelected]}
                >
                  <Text style={[styles.modeTitle, selected && styles.modeTitleSelected]}>{label}</Text>
                  <Text style={styles.modeDescription}>
                    {value === 'CURRENT'
                      ? 'I already own these investments.'
                      : 'I want to evaluate amounts before investing.'}
                  </Text>
                </Pressable>
              );
            })}
          </View>
          {mode === 'PLANNED' ? (
            <View>
              <Text style={styles.label}>PLAN CURRENCY</Text>
              <View style={styles.currencyControl}>
                {(['USD', 'THB'] as PortfolioCurrency[]).map((currency) => {
                  const selected = planCurrency === currency;
                  return (
                    <Pressable
                      accessibilityLabel={`${currency} plan currency`}
                      accessibilityRole="radio"
                      accessibilityState={{ selected, disabled: saving }}
                      disabled={saving}
                      key={currency}
                      onPress={() => setPlanCurrency(currency)}
                      style={[styles.currencyOption, selected && styles.currencyOptionSelected]}
                    >
                      <Text style={[styles.currencyText, selected && styles.currencyTextSelected]}>{currency}</Text>
                    </Pressable>
                  );
                })}
              </View>
            </View>
          ) : null}
        </Card>

        <View style={styles.sectionHeader}>
          <View style={{ flex: 1 }}>
            <Text style={styles.sectionTitle}>Holdings</Text>
            <Text style={styles.sectionText}>
              Add each position in the order you want it displayed.
            </Text>
          </View>
          <Pressable
            accessibilityLabel="Add holding"
            accessibilityRole="button"
            accessibilityState={{ disabled: saving }}
            style={styles.addButton}
            onPress={addRow}
            disabled={saving}
          >
            <Ionicons name="add" size={17} color={colors.onPrimary} />
          </Pressable>
        </View>

        <View style={styles.rows}>
          {rows.map((row, index) => (
            <Card key={row.id} style={styles.assetCard}>
              <View style={styles.assetHeader}>
                <Text style={styles.assetNumber}>HOLDING {index + 1}</Text>
                <View style={styles.assetActions}>
                  <Pressable
                    accessibilityLabel={`Move holding ${index + 1} up`}
                    accessibilityRole="button"
                    accessibilityState={{ disabled: saving || index === 0 }}
                    hitSlop={5}
                    onPress={() => moveRow(index, -1)}
                    disabled={saving || index === 0}
                    style={styles.iconButton}
                  >
                    <Ionicons
                      name="arrow-up"
                      size={17}
                      color={index === 0 ? colors.muted : colors.textSecondary}
                    />
                  </Pressable>
                  <Pressable
                    accessibilityLabel={`Move holding ${index + 1} down`}
                    accessibilityRole="button"
                    accessibilityState={{
                      disabled: saving || index === rows.length - 1
                    }}
                    hitSlop={5}
                    onPress={() => moveRow(index, 1)}
                    disabled={saving || index === rows.length - 1}
                    style={styles.iconButton}
                  >
                    <Ionicons
                      name="arrow-down"
                      size={17}
                      color={index === rows.length - 1
                        ? colors.muted
                        : colors.textSecondary}
                    />
                  </Pressable>
                  <Pressable
                    accessibilityLabel={`Remove holding ${index + 1}`}
                    accessibilityRole="button"
                    onPress={() => setRows((current) => (
                      current.filter((item) => item.id !== row.id)
                    ))}
                    disabled={saving}
                    style={styles.iconButton}
                  >
                    <Ionicons
                      name="trash-outline"
                      size={18}
                      color={colors.danger}
                    />
                  </Pressable>
                </View>
              </View>

              <View>
                <Text style={styles.label}>Symbol</Text>
                <AssetSymbolField
                  value={row.symbol}
                  onChangeText={(symbol) => patchRow(row.id, { symbol })}
                  editable={!saving}
                  error={fieldIssue(index, 'symbol')}
                />
              </View>

              {mode === 'PLANNED' && 'proposedAmount' in row ? (
                <HoldingDecimalInput
                  label={`Proposed Amount (${planCurrency})`}
                  value={row.proposedAmount}
                  onValueChange={(proposedAmount) =>
                    patchRow(row.id, { proposedAmount })
                  }
                  placeholder="4000.00"
                  editable={!saving}
                  error={fieldIssue(index, 'proposed_amount')}
                />
              ) : 'shares' in row ? (
                <HoldingDecimalInput
                  label="Quantity Owned"
                  value={row.shares}
                  onValueChange={(shares) =>
                    patchRow(row.id, { shares })
                  }
                  placeholder="10.5"
                  editable={!saving}
                  error={fieldIssue(index, 'shares')}
                />
              ) : null}
            </Card>
          ))}
        </View>

        <Pressable
          accessibilityLabel="Add another holding"
          accessibilityRole="button"
          accessibilityState={{ disabled: saving }}
          style={styles.textButton}
          onPress={addRow}
          disabled={saving}
        >
          <Ionicons name="add-circle-outline" size={17} color={colors.primary} />
          <Text style={styles.textButtonLabel}>Add Holding</Text>
        </Pressable>

        <Card style={styles.allocationNote}>
          <Ionicons name="sparkles-outline" size={20} color={colors.primary} />
          <View style={styles.allocationNoteText}>
            <Text style={styles.allocationNoteTitle}>Automatic allocation</Text>
            <Text style={styles.allocationNoteBody}>
              {mode === 'PLANNED'
                ? 'Aura calculates target percentages from proposed amounts. Estimated shares are display-only and the plan still saves when price data is unavailable.'
                : 'After saving, Aura uses market prices to value your shares and calculate the current percentage for each holding.'}
            </Text>
          </View>
        </Card>

        {submitMessage ? (
          <View style={styles.formError}>
            <FormErrorSummary error={submitError} message={submitMessage} />
            {partialPortfolioId ? (
              <Button
                title="View created portfolio"
                variant="secondary"
                onPress={() => navigation.replace('PortfolioDetail', {
                  portfolioId: partialPortfolioId
                })}
              />
            ) : null}
          </View>
        ) : null}

        <View style={styles.footerActions}>
          <Button
            title="Cancel"
            variant="secondary"
            style={styles.footerSecondary}
            onPress={() => navigation.goBack()}
            disabled={saving}
          />
          <Button
            title={saving ? 'Creating…' : 'Create Portfolio'}
            style={styles.footerPrimary}
            onPress={save}
            disabled={saving}
          />
        </View>
      </KeyboardAwareScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 100 },
  formCard: { marginTop: spacing.xl },
  modeCard: { marginTop: spacing.md, gap: spacing.md },
  modeControl: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  modeOption: {
    flexGrow: 1,
    flexBasis: 150,
    minHeight: 72,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceAlt,
    padding: spacing.md
  },
  modeOptionSelected: {
    borderColor: colors.primary,
    backgroundColor: colors.selectedBackground
  },
  modeTitle: { color: colors.textSecondary, fontSize: 12, fontWeight: '900' },
  modeTitleSelected: { color: colors.primary },
  modeDescription: { color: colors.muted, fontSize: 10, lineHeight: 15, marginTop: 4 },
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
    width: 44,
    height: 44,
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
  assetActions: { flexDirection: 'row', alignItems: 'center', gap: spacing.xs },
  iconButton: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center'
  },
  assetNumber: {
    color: colors.primary,
    fontSize: 9,
    fontWeight: '900',
    letterSpacing: 1
  },
  inline: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md, alignItems: 'flex-end' },
  amountField: { flexGrow: 1, flexBasis: 150 },
  label: {
    color: colors.textSecondary,
    fontSize: 10,
    fontWeight: '800',
    marginBottom: 6
  },
  compactInput: { minHeight: 48 },
  currencyField: { flexGrow: 1, flexBasis: 150, gap: spacing.sm },
  currencyControl: {
    minHeight: 48,
    flexDirection: 'row',
    borderRadius: 15,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceAlt,
    padding: spacing.xs
  },
  currencyOption: {
    flex: 1,
    borderRadius: 11,
    alignItems: 'center',
    justifyContent: 'center'
  },
  currencyOptionSelected: { backgroundColor: colors.selectedBackground },
  currencyText: { color: colors.muted, fontSize: 12, fontWeight: '900' },
  currencyTextSelected: { color: colors.primary },
  allocationNote: {
    marginTop: spacing.xl,
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.md,
    backgroundColor: colors.summaryBackground
  },
  textButton: {
    minHeight: 44,
    flexDirection: 'row',
    gap: 7,
    alignItems: 'center',
    marginTop: spacing.md,
    alignSelf: 'flex-start'
  },
  textButtonLabel: { color: colors.primary, fontSize: 11, fontWeight: '900' },
  allocationNoteText: { flex: 1 },
  allocationNoteTitle: { color: colors.text, fontWeight: '900' },
  allocationNoteBody: {
    color: colors.textSecondary,
    fontSize: 11,
    lineHeight: 17,
    marginTop: spacing.xs
  },
  formError: { gap: spacing.sm, marginTop: spacing.lg },
  footerActions: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md, marginTop: spacing.xl },
  footerSecondary: { flexGrow: 1, flexBasis: 120 },
  footerPrimary: { flexGrow: 1.35, flexBasis: 160 }
});
