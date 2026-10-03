import { usePrivateValue } from '../../privacy/PortfolioPrivacy';
import React, { useCallback, useRef, useState } from 'react';
import {
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';

import { DonutAllocationChart } from '../../components/charts/DonutAllocationChart';
import { ConfirmationDialog } from '../../components/ui/ConfirmationDialog';
import { AssetRow } from '../../components/portfolio/AssetRow';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { FormErrorSummary, InlineErrorCard, ScreenErrorState } from '../../components/ui/ErrorState';
import { LoadingState } from '../../components/ui/LoadingState';
import { PageTitle } from '../../components/ui/PageTitle';
import { SectionHeader } from '../../components/ui/SectionHeader';
import {
  isPortfolioMarketDataUnavailable,
  PORTFOLIO_MARKET_DATA_RECOVERY_MESSAGE,
  portfolioErrorMessage,
  portfolioValuationErrorMessage
} from '../../portfolio/portfolioErrors';
import {
  formatPortfolioMoney,
  formatPortfolioQuantity
} from '../../portfolio/portfolioFormatting';
import { decimalWeightToPercent } from '../../portfolio/portfolioValidation';
import { usePortfolios } from '../../portfolio/usePortfolios';
import { colors, spacing } from '../../theme/theme';
import {
  portfolioHoldingMode,
  type PortfolioCurrency,
  type PortfolioPlannedPreviewResponse,
  type PortfolioResponse,
  type PortfolioValuationResponse
} from '../../types/portfolio';

type LoadStatus = 'loading' | 'ready' | 'error';
type ValuationStatus = 'idle' | 'loading' | 'ready' | 'error';
type NameAction = 'rename' | 'duplicate' | null;

export function PortfolioDetailScreen({
  route,
  navigation
}: {
  route: any;
  navigation: any;
}) {
  const privateValue = usePrivateValue();
  const {
    getPortfolio,
    getPortfolioValuation,
    getPlannedPreview,
    selectPortfolio,
    renamePortfolio,
    duplicatePortfolio,
    deletePortfolio
  } = usePortfolios();
  const portfolioId = route.params.portfolioId as string;
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);
  const [loadStatus, setLoadStatus] = useState<LoadStatus>('loading');
  const [loadError, setLoadError] = useState<unknown>(null);
  const [currency, setCurrency] = useState<PortfolioCurrency>('USD');
  const [valuation, setValuation] = useState<PortfolioValuationResponse | null>(null);
  const [plannedPreview, setPlannedPreview] = useState<PortfolioPlannedPreviewResponse | null>(null);
  const [valuationStatus, setValuationStatus] = useState<ValuationStatus>('idle');
  const [valuationError, setValuationError] = useState<unknown>(null);
  const [nameAction, setNameAction] = useState<NameAction>(null);
  const [draftName, setDraftName] = useState('');
  const [pendingAction, setPendingAction] = useState<NameAction | 'delete'>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [actionError, setActionError] = useState<unknown>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const loadRequestRef = useRef(0);
  const actionPendingRef = useRef(false);

  const loadPortfolio = useCallback(async () => {
    const requestId = loadRequestRef.current + 1;
    loadRequestRef.current = requestId;
    setLoadStatus((current) => current === 'ready' ? 'ready' : 'loading');
    setLoadError(null);

    try {
      const response = await getPortfolio(portfolioId);
      if (loadRequestRef.current !== requestId) return;
      setPortfolio(response);
      selectPortfolio(response.id);
      setLoadStatus('ready');

      if (response.portfolio_type === 'PLANNED' && response.holdings.length) {
        setValuation(null);
        setValuationStatus('loading');
        setValuationError(null);
        try {
          const preview = await getPlannedPreview(response.id);
          if (loadRequestRef.current !== requestId) return;
          setPlannedPreview(preview);
          setValuationStatus('ready');
        } catch (error) {
          if (loadRequestRef.current !== requestId) return;
          setPlannedPreview(null);
          setValuationError(error);
          setValuationStatus('error');
        }
      } else if (portfolioHoldingMode(response.holdings) === 'real') {
        setPlannedPreview(null);
        setValuationStatus('loading');
        setValuationError(null);
        try {
          const currentValuation = await getPortfolioValuation(
            response.id,
            currency
          );
          if (loadRequestRef.current !== requestId) return;
          setValuation(currentValuation);
          setValuationStatus('ready');
        } catch (error) {
          if (loadRequestRef.current !== requestId) return;
          setValuationError(error);
          setValuationStatus('error');
        }
      } else {
        setValuation(null);
        setPlannedPreview(null);
        setValuationError(null);
        setValuationStatus('idle');
      }
    } catch (error) {
      if (loadRequestRef.current !== requestId) return;
      setLoadError(error);
      setLoadStatus('error');
    }
  }, [currency, getPlannedPreview, getPortfolio, getPortfolioValuation, portfolioId, selectPortfolio]);

  useFocusEffect(useCallback(() => {
    void loadPortfolio();
    return () => {
      loadRequestRef.current += 1;
    };
  }, [loadPortfolio]));

  function openNameAction(action: Exclude<NameAction, null>) {
    if (!portfolio || actionPendingRef.current) return;
    setDraftName(
      action === 'rename' ? portfolio.name : `${portfolio.name} Copy`
    );
    setActionError(null);
    setActionMessage(null);
    setNameAction(action);
  }

  async function submitNameAction() {
    if (!portfolio || !nameAction || actionPendingRef.current) return;
    const normalizedName = draftName.trim();
    if (!normalizedName) {
      setActionError(null);
      setActionMessage('Enter a portfolio name.');
      return;
    }

    const action = nameAction;
    actionPendingRef.current = true;
    setPendingAction(action);
    setActionError(null);
    setActionMessage(null);
    try {
      if (action === 'rename') {
        const updated = await renamePortfolio(portfolio.id, normalizedName);
        setPortfolio(updated);
        setNameAction(null);
      } else {
        const duplicate = await duplicatePortfolio(portfolio.id, normalizedName);
        setNameAction(null);
        navigation.replace('PortfolioDetail', { portfolioId: duplicate.id });
      }
    } catch (error) {
      setActionError(error);
      setActionMessage(portfolioErrorMessage(error));
    } finally {
      actionPendingRef.current = false;
      setPendingAction(null);
    }
  }

  function confirmDelete() {
    if (!portfolio || actionPendingRef.current) return;
    setActionError(null);
    setActionMessage(null);
    setDeleteOpen(true);
  }

  async function submitDelete() {
    if (!portfolio || actionPendingRef.current) return;
    actionPendingRef.current = true;
    setPendingAction('delete');
    try {
      setActionError(null);
      setActionMessage(null);
      await deletePortfolio(portfolio.id);
      setDeleteOpen(false);
      navigation.popToTop();
    } catch (error) {
      setActionError(error);
      setActionMessage(portfolioErrorMessage(error));
    } finally {
      actionPendingRef.current = false;
      setPendingAction(null);
    }
  }

  if (loadStatus === 'loading' && !portfolio) {
    return <LoadingState message="Loading portfolio…" />;
  }

  if (!portfolio) {
    return (
      <SafeAreaView style={styles.safe} edges={['bottom']}>
        <ScreenErrorState
          error={loadError}
          resourceName="Portfolio"
          fallbackMessage="Unable to load this portfolio."
          onRetry={() => void loadPortfolio()}
          onBack={() => navigation.popToTop()}
          backTitle="Back to portfolios"
        />
      </SafeAreaView>
    );
  }

  const holdingMode = portfolioHoldingMode(portfolio.holdings);
  const marketDataUnavailable = isPortfolioMarketDataUnavailable(valuationError);
  const valuationById = new Map(
    valuation?.holdings.map((holding) => [holding.id, holding]) ?? []
  );

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content}>
        <PageTitle
          eyebrow={portfolio.portfolio_type === 'PLANNED'
            ? 'PLANNED · HYPOTHETICAL'
            : holdingMode === 'real'
              ? 'REAL HOLDINGS'
              : holdingMode === 'legacy'
                ? 'LEGACY ALLOCATION'
                : undefined}
          title={portfolio.name}
          subtitle={`${portfolio.holdings.length} holdings · Updated ${new Date(portfolio.updated_at).toLocaleDateString()}`}
        />

        {loadStatus === 'error' ? (
          <InlineErrorCard
            error={loadError}
            message={portfolioErrorMessage(loadError, 'Unable to refresh this portfolio.')}
            stale
            onRetry={() => void loadPortfolio()}
          />
        ) : null}

        <View style={styles.primaryActions}>
          <Button
            title="Analyze Portfolio"
            style={{ flex: 1.25 }}
            onPress={() => navigation.navigate('PortfolioAnalysis', {
              portfolioId: portfolio.id
            })}
            disabled={pendingAction !== null}
          />
          <Button
            title="Edit Holdings"
            variant="secondary"
            style={{ flex: 1 }}
            onPress={() => navigation.navigate('EditHoldings', {
              portfolioId: portfolio.id
            })}
            disabled={pendingAction !== null}
          />
        </View>

        {portfolio.portfolio_type === 'PLANNED' ? (
          <>
            <View style={styles.valuationHeader}>
              <Text style={styles.valuationHeading}>Proposed Investment</Text>
            </View>
            {valuationStatus === 'loading' ? (
              <Card><Text style={styles.stateText}>Loading planned allocation and optional share estimates…</Text></Card>
            ) : valuationStatus === 'error' ? (
              <InlineErrorCard
                error={valuationError}
                message={portfolioErrorMessage(valuationError, 'Unable to load the planned portfolio preview.')}
                onRetry={() => void loadPortfolio()}
                retryTitle="Retry preview"
              />
            ) : plannedPreview ? (
              <Card style={styles.valueCard}>
                <Text style={styles.totalValue}>
                  {privateValue(formatPortfolioMoney(plannedPreview.total_proposed_amount, plannedPreview.plan_currency))}
                </Text>
                <Text style={styles.valueMeta}>
                  Plan currency {plannedPreview.plan_currency} · preview requested {plannedPreview.requested_date}
                </Text>
                <Text style={styles.valueMeta}>
                  Estimated shares are display-only. Target allocation comes only from proposed amounts.
                </Text>
              </Card>
            ) : null}
          </>
        ) : holdingMode === 'real' ? (
          <>
            <View style={styles.valuationHeader}>
              <Text style={styles.valuationHeading}>Current Value</Text>
              <View style={styles.currencyControl}>
                {(['USD', 'THB'] as PortfolioCurrency[]).map((option) => {
                  const selected = currency === option;
                  return (
                    <Pressable
                      accessibilityLabel={`${option} valuation currency`}
                      accessibilityRole="radio"
                      accessibilityState={{ selected }}
                      key={option}
                      onPress={() => {
                        if (option !== currency) setValuation(null);
                        setCurrency(option);
                      }}
                      style={[styles.currencyOption, selected && styles.currencyOptionSelected]}
                    >
                      <Text style={[styles.currencyText, selected && styles.currencyTextSelected]}>{option}</Text>
                    </Pressable>
                  );
                })}
              </View>
            </View>
            {valuationStatus === 'loading' ? (
              <Card><Text style={styles.stateText}>Loading current portfolio value…</Text></Card>
            ) : valuationStatus === 'error' ? (
              <InlineErrorCard
                error={valuationError}
                message={portfolioValuationErrorMessage(valuationError)}
                stale={marketDataUnavailable || Boolean(valuation)}
                staleMessage={marketDataUnavailable
                  ? PORTFOLIO_MARKET_DATA_RECOVERY_MESSAGE
                  : undefined}
                onRetry={() => void loadPortfolio()}
                retryTitle="Retry Current Value"
                compactAction
              />
            ) : valuation ? (
              <Card style={styles.valueCard}>
                <Text style={styles.totalValue}>{privateValue(formatPortfolioMoney(valuation.total_current_value, valuation.valuation_currency))}</Text>
                <Text style={styles.valueMeta}>
                  Requested {valuation.requested_date} · prices {valuation.oldest_price_as_of} to {valuation.newest_price_as_of}
                </Text>
                {valuation.fx ? (
                  <Text style={styles.valueMeta}>USD/THB {formatPortfolioQuantity(valuation.fx.rate)} · {valuation.fx.as_of}</Text>
                ) : null}
              </Card>
            ) : null}
          </>
        ) : holdingMode === 'legacy' ? (
          <Card style={styles.legacyCard}>
            <Text style={styles.legacyTitle}>Legacy saved allocation</Text>
            <Text style={styles.legacyText}>These percentages remain readable. Edit holdings to replace them with real position facts and enable current valuation.</Text>
          </Card>
        ) : holdingMode === 'mixed' ? (
          <Card style={styles.valuationErrorCard}>
            <Text style={styles.errorTitle}>Mixed holdings cannot be valued</Text>
            <Text style={styles.errorText}>Edit the complete holdings list to convert every position to the real-holding format.</Text>
          </Card>
        ) : null}

        <SectionHeader title={portfolio.portfolio_type === 'PLANNED'
          ? 'Target Allocation'
          : holdingMode === 'real'
            ? 'Current Allocation'
            : 'Allocation'} />
        {portfolio.portfolio_type === 'PLANNED' && plannedPreview ? (
          <Card>
            <DonutAllocationChart
              data={plannedPreview.holdings.map((holding) => ({
                symbol: holding.symbol,
                weight: Number(holding.target_allocation) * 100
              }))}
            />
          </Card>
        ) : holdingMode === 'legacy' ? (
          <Card>
            <DonutAllocationChart
              data={portfolio.holdings.map((holding) => ({
                symbol: holding.symbol,
                weight: decimalWeightToPercent(holding.weight ?? 0)
              }))}
            />
          </Card>
        ) : holdingMode === 'real' && valuation ? (
          <Card>
            <DonutAllocationChart
              data={valuation.holdings.map((holding) => ({
                symbol: holding.symbol,
                weight: Number(holding.current_allocation) * 100
              }))}
            />
          </Card>
        ) : portfolio.holdings.length ? (
          <Card>
            <EmptyState
              title={portfolio.portfolio_type === 'PLANNED'
                ? 'Target allocation unavailable'
                : 'Current allocation unavailable'}
              description={portfolio.portfolio_type === 'PLANNED'
                ? 'Retry to load the target allocation calculated from your proposed amounts.'
                : 'Aura can display current allocation after market prices are available.'}
            />
          </Card>
        ) : (
          <Card>
            <EmptyState
              title="No holdings yet"
              description={portfolio.portfolio_type === 'PLANNED'
                ? 'Add proposed investment amounts to complete this plan.'
                : 'Add real holding facts to complete this portfolio.'}
            />
          </Card>
        )}

        <SectionHeader
          title="Holdings"
          action={portfolio.holdings.length ? 'Edit' : 'Add'}
          onPress={() => navigation.navigate(
            portfolio.holdings.length ? 'EditHoldings' : 'AddAsset',
            { portfolioId: portfolio.id }
          )}
        />
        {portfolio.holdings.length ? (
          <Card>
            {portfolio.holdings.map((holding) => (
              <AssetRow
                key={holding.symbol}
                holding={holding}
                valuation={valuationById.get(holding.id)}
                plannedPreview={plannedPreview?.holdings.find((item) => item.id === holding.id)}
                valuationCurrency={plannedPreview?.plan_currency ?? portfolio.plan_currency ?? valuation?.valuation_currency}
              />
            ))}
          </Card>
        ) : null}

        <SectionHeader title="Portfolio Details" />
        <Card style={styles.metadataCard}>
          <View style={styles.metadataRow}>
            <Text style={styles.metadataLabel}>Created</Text>
            <Text style={styles.metadataValue}>
              {new Date(portfolio.created_at).toLocaleString()}
            </Text>
          </View>
          <View style={styles.metadataRow}>
            <Text style={styles.metadataLabel}>Updated</Text>
            <Text style={styles.metadataValue}>
              {new Date(portfolio.updated_at).toLocaleString()}
            </Text>
          </View>
        </Card>

        <SectionHeader title="Portfolio Actions" />
        {actionMessage && !nameAction ? (
          <FormErrorSummary error={actionError} message={actionMessage} />
        ) : null}
        <View style={styles.actionGrid}>
          <Button
            title={pendingAction === 'rename' ? 'Renaming…' : 'Rename'}
            variant="secondary"
            style={{ flex: 1 }}
            onPress={() => openNameAction('rename')}
            disabled={pendingAction !== null}
          />
          <Button
            title={pendingAction === 'duplicate' ? 'Duplicating…' : 'Duplicate'}
            variant="secondary"
            style={{ flex: 1 }}
            onPress={() => openNameAction('duplicate')}
            disabled={pendingAction !== null}
          />
        </View>
        <Button
          title={pendingAction === 'delete' ? 'Deleting…' : 'Delete Portfolio'}
          variant="danger"
          style={{ marginTop: spacing.md }}
          onPress={confirmDelete}
          disabled={pendingAction !== null}
        />
      </ScrollView>

      <Modal
        visible={nameAction !== null}
        transparent
        animationType="fade"
        onRequestClose={() => {
          if (!actionPendingRef.current) setNameAction(null);
        }}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={styles.modalAvoidingView}
        >
          <View style={styles.modalBackdrop}>
            <View style={styles.modalCard}>
              <View style={styles.modalHeader}>
                <Text style={styles.modalTitle}>
                  {nameAction === 'rename' ? 'Rename portfolio' : 'Duplicate portfolio'}
                </Text>
                <Pressable
                  accessibilityLabel="Close portfolio name editor"
                  accessibilityRole="button"
                  accessibilityState={{ disabled: pendingAction !== null }}
                  style={styles.closeButton}
                  onPress={() => setNameAction(null)}
                  disabled={pendingAction !== null}
                >
                  <Ionicons name="close" color={colors.text} size={20} />
                </Pressable>
              </View>
              <Text style={styles.inputLabel}>Portfolio name</Text>
              <TextInput
                accessibilityLabel="Portfolio name"
                accessibilityState={{ disabled: pendingAction !== null }}
                value={draftName}
                onChangeText={(value) => {
                  setDraftName(value);
                  setActionError(null);
                  setActionMessage(null);
                }}
                style={styles.input}
                placeholder="Portfolio name"
                placeholderTextColor={colors.muted}
                autoCapitalize="words"
                editable={pendingAction === null}
              />
              {actionMessage ? (
                <FormErrorSummary error={actionError} message={actionMessage} />
              ) : null}
              <View style={styles.modalActions}>
                <Button
                  title="Cancel"
                  variant="secondary"
                  style={{ flex: 1 }}
                  onPress={() => setNameAction(null)}
                  disabled={pendingAction !== null}
                />
                <Button
                  title={pendingAction ? 'Saving…' : 'Save'}
                  style={{ flex: 1 }}
                  onPress={submitNameAction}
                  disabled={pendingAction !== null}
                />
              </View>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
      <ConfirmationDialog
        visible={deleteOpen}
        title="Delete portfolio?"
        description="This permanently deletes the portfolio and its saved holdings. This action cannot be undone."
        subjectLabel="Portfolio"
        subject={portfolio.name}
        confirmLabel="Delete Portfolio"
        busy={pendingAction === 'delete'}
        errorMessage={deleteOpen ? actionMessage : null}
        onCancel={() => { if (!actionPendingRef.current) { setDeleteOpen(false); setActionError(null); setActionMessage(null); } }}
        onConfirm={() => void submitDelete()}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 100 },
  primaryActions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
    marginTop: spacing.xl
  },
  valuationHeader: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: spacing.xl,
    marginBottom: spacing.md
  },
  valuationHeading: { color: colors.text, fontSize: 18, fontWeight: '900' },
  currencyControl: { flexDirection: 'row', backgroundColor: colors.surfaceAlt, borderRadius: 12, padding: 3 },
  currencyOption: { minHeight: 44, justifyContent: 'center', paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderRadius: 9 },
  currencyOptionSelected: { backgroundColor: colors.selectedBackground },
  currencyText: { color: colors.muted, fontSize: 11, fontWeight: '900' },
  currencyTextSelected: { color: colors.primary },
  valueCard: { gap: spacing.sm, backgroundColor: colors.summaryBackground },
  totalValue: { color: colors.text, fontSize: 28, fontWeight: '900' },
  valueMeta: { color: colors.textSecondary, fontSize: 10, lineHeight: 16 },
  stateText: { color: colors.textSecondary, fontSize: 12 },
  valuationErrorCard: { gap: spacing.md, borderColor: colors.dangerBorder },
  legacyCard: { marginTop: spacing.xl, backgroundColor: colors.warningBackground },
  legacyTitle: { color: colors.warning, fontWeight: '900' },
  legacyText: { color: colors.textSecondary, fontSize: 11, lineHeight: 17, marginTop: spacing.xs },
  metadataCard: { gap: spacing.md },
  metadataRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    gap: spacing.md
  },
  metadataLabel: { color: colors.textSecondary, fontSize: 11 },
  metadataValue: { color: colors.text, fontSize: 11, fontWeight: '800' },
  actionGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  errorWrap: { flex: 1, justifyContent: 'center', padding: spacing.xl },
  errorCard: { gap: spacing.md },
  errorTitle: { color: colors.danger, fontSize: 16, fontWeight: '900' },
  errorText: { color: colors.textSecondary, fontSize: 12, lineHeight: 18 },
  modalBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.55)',
    justifyContent: 'center',
    padding: spacing.xl
  },
  modalAvoidingView: { flex: 1 },
  modalCard: {
    backgroundColor: colors.surface,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg
  },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md
  },
  modalTitle: { color: colors.text, fontSize: 19, fontWeight: '900' },
  closeButton: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: colors.surfaceAlt,
    alignItems: 'center',
    justifyContent: 'center'
  },
  inputLabel: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: '800',
    marginTop: spacing.xl,
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
    fontSize: 14
  },
  modalActions: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md, marginTop: spacing.xl }
});
