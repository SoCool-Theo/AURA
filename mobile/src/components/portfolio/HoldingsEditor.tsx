import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Pressable,
  StyleSheet,
  Text,
  type TextInput,
  View
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import { apiValidationIssues } from '../../api/apiErrorPresentation';
import { portfolioErrorMessage } from '../../portfolio/portfolioErrors';
import {
  apiPortfolioInputWarning,
  localHoldingInputWarning,
  showPortfolioInputWarning,
  type PortfolioInputWarning
} from '../../portfolio/portfolioInputWarning';
import {
  createPlannedHoldingDraft,
  createRealHoldingDraft,
  plannedHoldingToDraft,
  realHoldingToDraft,
  type PlannedHoldingDraft,
  type RealHoldingDraft,
  validatePlannedHoldingDrafts,
  validateRealHoldingDrafts
} from '../../portfolio/portfolioValidation';
import { usePortfolios } from '../../portfolio/usePortfolios';
import { colors, spacing, typography } from '../../theme/theme';
import {
  isRealPortfolioHolding,
  isPlannedPortfolioHolding,
  portfolioHoldingMode,
  type PortfolioCurrency,
  type PortfolioHoldingMode,
  type PortfolioPlannedHoldingInput,
  type PortfolioRealHoldingInput
} from '../../types/portfolio';
import { AssetSymbolField } from './AssetSymbolField';
import { HoldingDecimalInput } from './HoldingDecimalInput';
import { PurchaseDateField } from './PurchaseDateField';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { FormErrorSummary, ScreenErrorState } from '../ui/ErrorState';
import { KeyboardAwareScrollView } from '../ui/KeyboardAwareScrollView';
import { LoadingState } from '../ui/LoadingState';

type LoadStatus = 'loading' | 'ready' | 'error';
type HoldingDraft = RealHoldingDraft | PlannedHoldingDraft;

export function HoldingsEditor({
  portfolioId,
  navigation,
  startWithBlankRow = false
}: {
  portfolioId: string;
  navigation: any;
  startWithBlankRow?: boolean;
}) {
  const { getPortfolio, replacePlannedHoldings, replaceRealHoldings } = usePortfolios();
  const [portfolioName, setPortfolioName] = useState('Portfolio');
  const [planCurrency, setPlanCurrency] = useState<PortfolioCurrency | null>(null);
  const [holdingMode, setHoldingMode] = useState<PortfolioHoldingMode>('empty');
  const [rows, setRows] = useState<HoldingDraft[]>([]);
  const [loadStatus, setLoadStatus] = useState<LoadStatus>('loading');
  const [loadError, setLoadError] = useState<unknown>(null);
  const [saving, setSaving] = useState(false);
  const [submitError, setSubmitError] = useState<unknown>(null);
  const [submitMessage, setSubmitMessage] = useState<string | null>(null);
  const [inputWarning, setInputWarning] = useState<PortfolioInputWarning | null>(null);
  const requestRef = useRef(0);
  const submittingRef = useRef(false);
  const fieldRefs = useRef(new Map<string, TextInput>());

  function inputKeys() {
    return {
      emptyHoldings: 'edit-add-holding',
      rows: rows.map((row) => ({
        symbol: `edit-${row.id}-symbol`,
        shares: `edit-${row.id}-shares`,
        proposedAmount: `edit-${row.id}-proposed-amount`
      }))
    };
  }

  function revealField(fieldKey: string) {
    if (fieldKey === 'edit-add-holding') {
      const existing = rows[0];
      if (existing) {
        fieldRefs.current.get(`edit-${existing.id}-symbol`)?.focus();
        return;
      }
      const row = holdingMode === 'planned'
        ? createPlannedHoldingDraft()
        : createRealHoldingDraft();
      const symbolKey = `edit-${row.id}-symbol`;
      setRows([row]);
      setInputWarning((current) => current
        ? { ...current, fieldKey: symbolKey }
        : current);
      setTimeout(() => {
        fieldRefs.current.get(symbolKey)?.focus();
      }, 120);
      return;
    }
    fieldRefs.current.get(fieldKey)?.focus();
  }

  function presentInputWarning(warning: PortfolioInputWarning) {
    setInputWarning(warning);
    showPortfolioInputWarning(warning, revealField);
  }

  function fieldRef(fieldKey: string) {
    return (input: TextInput | null) => {
      if (input) fieldRefs.current.set(fieldKey, input);
      else fieldRefs.current.delete(fieldKey);
    };
  }

  const loadPortfolio = useCallback(async () => {
    const requestId = requestRef.current + 1;
    requestRef.current = requestId;
    setLoadStatus('loading');
    setLoadError(null);

    try {
      const portfolio = await getPortfolio(portfolioId);
      if (requestRef.current !== requestId) return;
      const mode = portfolio.portfolio_type === 'PLANNED'
        ? 'planned'
        : portfolioHoldingMode(portfolio.holdings);
      const loadedRows: HoldingDraft[] = portfolio.holdings.map((holding) => {
        if (isPlannedPortfolioHolding(holding)) return plannedHoldingToDraft(holding);
        if (isRealPortfolioHolding(holding)) return realHoldingToDraft(holding);
        return createRealHoldingDraft({ symbol: holding.symbol });
      });
      if (startWithBlankRow || !loadedRows.length) {
        loadedRows.push(portfolio.portfolio_type === 'PLANNED'
          ? createPlannedHoldingDraft()
          : createRealHoldingDraft());
      }
      setPortfolioName(portfolio.name);
      setPlanCurrency(portfolio.plan_currency);
      setHoldingMode(mode);
      setRows(loadedRows);
      setInputWarning(null);
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
    setSubmitError(null);
    setSubmitMessage(null);
    setInputWarning(null);
    setRows((current) => current.map((row) => (
      row.id === id ? { ...row, ...patch } : row
    )));
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
    const planned = holdingMode === 'planned';
    const validation = planned
      ? validatePlannedHoldingDrafts(rows as PlannedHoldingDraft[])
      : validateRealHoldingDrafts(rows as RealHoldingDraft[]);
    if (!validation.holdings) {
      setSubmitError(null);
      setSubmitMessage(validation.error);
      presentInputWarning(localHoldingInputWarning(validation.issue, inputKeys()));
      return;
    }

    submittingRef.current = true;
    setSaving(true);
    setSubmitError(null);
    setSubmitMessage(null);
    try {
      if (planned) {
        await replacePlannedHoldings(
          portfolioId,
          validation.holdings as PortfolioPlannedHoldingInput[]
        );
      } else {
        await replaceRealHoldings(
          portfolioId,
          validation.holdings as PortfolioRealHoldingInput[]
        );
      }
      navigation.goBack();
    } catch (error) {
      setSubmitError(error);
      setSubmitMessage(portfolioErrorMessage(error));
      const warning = apiPortfolioInputWarning(error, inputKeys());
      if (warning) presentInputWarning(warning);
    } finally {
      submittingRef.current = false;
      setSaving(false);
    }
  }

  if (loadStatus === 'loading') {
    return <LoadingState message="Loading holdings…" />;
  }

  if (loadStatus === 'error') {
    return (
      <SafeAreaView style={styles.safe} edges={['bottom']}>
        <ScreenErrorState
          error={loadError}
          resourceName="Portfolio"
          fallbackMessage="Unable to load this portfolio."
          onRetry={() => void loadPortfolio()}
          onBack={() => navigation.goBack()}
        />
      </SafeAreaView>
    );
  }

  const validationIssues = apiValidationIssues(submitError);
  const fieldIssue = (index: number, field: string) => validationIssues.find(
    (issue) => issue.path.endsWith(`holdings.${index}.${field}`)
  )?.message;
  const visibleFieldError = (fieldKey: string, apiError?: string) => (
    inputWarning?.fieldKey === fieldKey ? inputWarning.message : apiError
  );

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <KeyboardAwareScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
      >
        <Text style={styles.title}>
          {startWithBlankRow ? 'Add holding' : 'Edit holdings'}
        </Text>
        <Text style={styles.subtitle}>
          {portfolioName}: submit the complete ordered list of {holdingMode === 'planned'
            ? 'proposed investments. Aura calculates target allocation from the saved amounts.'
            : 'positions. Aura calculates current allocation from market prices.'}
        </Text>

        {holdingMode === 'legacy' ? (
          <Card style={styles.warningCard}>
            <Text style={styles.warningTitle}>Convert legacy allocation</Text>
            <Text style={styles.warningText}>
              Enter a quantity owned for every saved symbol. Saving replaces the
              old manual weights with current holdings; this cannot create a mixed
              portfolio.
            </Text>
          </Card>
        ) : holdingMode === 'mixed' ? (
          <Card style={styles.errorCard}>
            <Text style={styles.errorTitle}>Holding state needs correction</Text>
            <Text style={styles.errorText}>
              This portfolio contains mixed holding modes. Enter a quantity owned
              for every current symbol before saving.
            </Text>
          </Card>
        ) : null}

        <View style={styles.list}>
          {rows.map((row, index) => (
            <Card key={row.id} style={styles.card}>
              <View style={styles.top}>
                <Text style={styles.rowTitle}>HOLDING {index + 1}</Text>
                <View style={styles.rowActions}>
                  <Pressable
                    accessibilityLabel={`Move holding ${index + 1} up`}
                    accessibilityRole="button"
                    accessibilityState={{ disabled: saving || index === 0 }}
                    disabled={saving || index === 0}
                    onPress={() => moveRow(index, -1)}
                    style={styles.iconButton}
                  >
                    <Ionicons name="arrow-up" size={17} color={index === 0 ? colors.muted : colors.textSecondary} />
                  </Pressable>
                  <Pressable
                    accessibilityLabel={`Move holding ${index + 1} down`}
                    accessibilityRole="button"
                    accessibilityState={{ disabled: saving || index === rows.length - 1 }}
                    disabled={saving || index === rows.length - 1}
                    onPress={() => moveRow(index, 1)}
                    style={styles.iconButton}
                  >
                    <Ionicons name="arrow-down" size={17} color={index === rows.length - 1 ? colors.muted : colors.textSecondary} />
                  </Pressable>
                  <Pressable
                    accessibilityLabel={`Remove holding ${index + 1}`}
                    accessibilityRole="button"
                    accessibilityState={{ disabled: saving }}
                    onPress={() => {
                      setSubmitError(null);
                      setSubmitMessage(null);
                      setInputWarning(null);
                      setRows((current) => (
                        current.filter((item) => item.id !== row.id)
                      ));
                    }}
                    style={styles.iconButton}
                    disabled={saving}
                  >
                    <Ionicons name="trash-outline" size={18} color={colors.danger} />
                  </Pressable>
                </View>
              </View>

              <View>
                <Text style={styles.fieldLabel}>Symbol</Text>
                <AssetSymbolField
                  ref={fieldRef(`edit-${row.id}-symbol`)}
                  value={row.symbol}
                  onChangeText={(symbol) => patchRow(row.id, { symbol })}
                  editable={!saving}
                  error={visibleFieldError(
                    `edit-${row.id}-symbol`,
                    fieldIssue(index, 'symbol')
                  )}
                />
              </View>

              {holdingMode === 'planned' && 'proposedAmount' in row ? (
                <HoldingDecimalInput
                  ref={fieldRef(`edit-${row.id}-proposed-amount`)}
                  label={`Proposed Amount (${planCurrency ?? 'USD'})`}
                  value={row.proposedAmount}
                  onValueChange={(proposedAmount) => patchRow(row.id, { proposedAmount })}
                  placeholder="4000.00"
                  editable={!saving}
                  error={visibleFieldError(
                    `edit-${row.id}-proposed-amount`,
                    fieldIssue(index, 'proposed_amount')
                  )}
                />
              ) : 'shares' in row ? (
              <HoldingDecimalInput
                ref={fieldRef(`edit-${row.id}-shares`)}
                label="Quantity Owned"
                value={row.shares}
                onValueChange={(shares) =>
                  patchRow(row.id, { shares })
                }
                placeholder="10.5"
                editable={!saving}
                error={visibleFieldError(
                  `edit-${row.id}-shares`,
                  fieldIssue(index, 'shares')
                )}
              />
            ) : null}
            </Card>
          ))}
        </View>

        <Pressable
          accessibilityLabel="Add holding"
          accessibilityRole="button"
          accessibilityState={{ disabled: saving }}
          style={styles.addRow}
          onPress={() => {
            setSubmitError(null);
            setSubmitMessage(null);
            setInputWarning(null);
            setRows((current) => [
              ...current,
              holdingMode === 'planned'
                ? createPlannedHoldingDraft()
                : createRealHoldingDraft()
            ]);
          }}
          disabled={saving}
        >
          <Ionicons name="add-circle-outline" size={17} color={colors.primary} />
          <Text style={styles.addRowText}>Add Holding</Text>
        </Pressable>

        <Card style={styles.infoCard}>
          <Ionicons name="sparkles-outline" size={19} color={colors.primary} />
          <Text style={styles.infoText}>
            {holdingMode === 'planned'
              ? 'Target allocation is calculated from proposed amounts; estimated shares are display-only.'
              : 'Allocation is calculated automatically after Aura values the saved shares.'}
          </Text>
        </Card>

        {submitMessage ? (
          <View style={styles.formError}>
            <FormErrorSummary error={submitError} message={submitMessage} />
          </View>
        ) : null}

        <Button
          title={saving ? 'Saving…' : holdingMode === 'planned' ? 'Save Planned Holdings' : 'Save Holdings'}
          onPress={save}
          disabled={saving}
          style={{ marginTop: spacing.xl }}
        />
      </KeyboardAwareScrollView>
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
  rowActions: { flexDirection: 'row', gap: spacing.xs },
  iconButton: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center'
  },
  fields: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md, alignItems: 'flex-end' },
  flexField: { flexGrow: 1, flexBasis: 150 },
  fieldLabel: {
    color: colors.muted,
    fontSize: 11,
    fontWeight: '800',
    marginBottom: spacing.sm
  },
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
  currencyOption: { flex: 1, borderRadius: 11, alignItems: 'center', justifyContent: 'center' },
  currencyOptionSelected: { backgroundColor: colors.selectedBackground },
  currencyText: { color: colors.muted, fontSize: 12, fontWeight: '900' },
  currencyTextSelected: { color: colors.primary },
  addRow: {
    minHeight: 44,
    flexDirection: 'row',
    gap: 7,
    alignItems: 'center',
    marginTop: spacing.md,
    alignSelf: 'flex-start'
  },
  addRowText: { color: colors.primary, fontSize: 11, fontWeight: '900' },
  infoCard: {
    marginTop: spacing.xl,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    backgroundColor: colors.summaryBackground
  },
  infoText: { color: colors.textSecondary, flex: 1, fontSize: 11, lineHeight: 17 },
  formError: { marginTop: spacing.lg },
  warningCard: { marginBottom: spacing.lg, borderColor: colors.warning },
  warningTitle: { color: colors.warning, fontWeight: '900' },
  warningText: { color: colors.textSecondary, fontSize: 11, lineHeight: 17, marginTop: spacing.xs },
  errorWrap: { flex: 1, justifyContent: 'center', padding: spacing.xl },
  errorCard: { gap: spacing.md },
  errorTitle: { color: colors.danger, fontSize: 16, fontWeight: '900' },
  errorText: { color: colors.textSecondary, fontSize: 12, lineHeight: 18 }
});
