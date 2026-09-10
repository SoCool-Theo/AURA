import React, { useCallback, useRef, useState } from 'react';
import {
  Alert,
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
import { AssetRow } from '../../components/portfolio/AssetRow';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { LoadingState } from '../../components/ui/LoadingState';
import { PageTitle } from '../../components/ui/PageTitle';
import { SectionHeader } from '../../components/ui/SectionHeader';
import { portfolioErrorMessage } from '../../portfolio/portfolioErrors';
import { decimalWeightToPercent } from '../../portfolio/portfolioValidation';
import { usePortfolios } from '../../portfolio/usePortfolios';
import { colors, spacing } from '../../theme/theme';
import type { PortfolioResponse } from '../../types/portfolio';

type LoadStatus = 'loading' | 'ready' | 'error';
type NameAction = 'rename' | 'duplicate' | null;

export function PortfolioDetailScreen({
  route,
  navigation
}: {
  route: any;
  navigation: any;
}) {
  const {
    getPortfolio,
    selectPortfolio,
    renamePortfolio,
    duplicatePortfolio,
    deletePortfolio
  } = usePortfolios();
  const portfolioId = route.params.portfolioId as string;
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);
  const [loadStatus, setLoadStatus] = useState<LoadStatus>('loading');
  const [loadError, setLoadError] = useState<unknown>(null);
  const [nameAction, setNameAction] = useState<NameAction>(null);
  const [draftName, setDraftName] = useState('');
  const [pendingAction, setPendingAction] = useState<NameAction | 'delete'>(null);
  const loadRequestRef = useRef(0);
  const actionPendingRef = useRef(false);

  const loadPortfolio = useCallback(async () => {
    const requestId = loadRequestRef.current + 1;
    loadRequestRef.current = requestId;
    setLoadStatus('loading');
    setLoadError(null);

    try {
      const response = await getPortfolio(portfolioId);
      if (loadRequestRef.current !== requestId) return;
      setPortfolio(response);
      selectPortfolio(response.id);
      setLoadStatus('ready');
    } catch (error) {
      if (loadRequestRef.current !== requestId) return;
      setPortfolio(null);
      setLoadError(error);
      setLoadStatus('error');
    }
  }, [getPortfolio, portfolioId, selectPortfolio]);

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
    setNameAction(action);
  }

  async function submitNameAction() {
    if (!portfolio || !nameAction || actionPendingRef.current) return;
    const normalizedName = draftName.trim();
    if (!normalizedName) {
      Alert.alert('Portfolio name required', 'Enter a portfolio name.');
      return;
    }

    const action = nameAction;
    actionPendingRef.current = true;
    setPendingAction(action);
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
      Alert.alert(
        action === 'rename' ? 'Unable to rename portfolio' : 'Unable to duplicate portfolio',
        portfolioErrorMessage(error)
      );
    } finally {
      actionPendingRef.current = false;
      setPendingAction(null);
    }
  }

  function confirmDelete() {
    if (!portfolio || actionPendingRef.current) return;
    Alert.alert(
      'Delete portfolio?',
      'This permanently deletes the portfolio and its holdings.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            if (actionPendingRef.current) return;
            actionPendingRef.current = true;
            setPendingAction('delete');
            try {
              await deletePortfolio(portfolio.id);
              navigation.popToTop();
            } catch (error) {
              Alert.alert(
                'Unable to delete portfolio',
                portfolioErrorMessage(error)
              );
            } finally {
              actionPendingRef.current = false;
              setPendingAction(null);
            }
          }
        }
      ]
    );
  }

  if (loadStatus === 'loading') {
    return <LoadingState message="Loading portfolio…" />;
  }

  if (loadStatus === 'error' || !portfolio) {
    return (
      <SafeAreaView style={styles.safe} edges={['bottom']}>
        <View style={styles.errorWrap}>
          <Card style={styles.errorCard}>
            <Text style={styles.errorTitle}>Unable to load portfolio</Text>
            <Text style={styles.errorText}>{portfolioErrorMessage(loadError)}</Text>
            <Button title="Retry" onPress={() => void loadPortfolio()} />
            <Button title="Back to portfolios" variant="secondary" onPress={() => navigation.popToTop()} />
          </Card>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content}>
        <PageTitle
          title={portfolio.name}
          subtitle={`${portfolio.holdings.length} holdings · Updated ${new Date(portfolio.updated_at).toLocaleDateString()}`}
        />

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

        <SectionHeader title="Allocation" />
        {portfolio.holdings.length ? (
          <Card>
            <DonutAllocationChart
              data={portfolio.holdings.map((holding) => ({
                symbol: holding.symbol,
                weight: decimalWeightToPercent(holding.weight)
              }))}
            />
          </Card>
        ) : (
          <Card>
            <EmptyState
              title="No holdings yet"
              description="Add symbols and percentage weights to complete this portfolio."
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
              <AssetRow key={holding.symbol} holding={holding} />
            ))}
          </Card>
        ) : null}

        <SectionHeader title="Backend Metadata" />
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
                  style={styles.closeButton}
                  onPress={() => setNameAction(null)}
                  disabled={pendingAction !== null}
                >
                  <Ionicons name="close" color={colors.text} size={20} />
                </Pressable>
              </View>
              <Text style={styles.inputLabel}>Portfolio name</Text>
              <TextInput
                value={draftName}
                onChangeText={setDraftName}
                style={styles.input}
                placeholder="Portfolio name"
                placeholderTextColor={colors.muted}
                autoCapitalize="words"
                editable={pendingAction === null}
              />
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
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 100 },
  primaryActions: {
    flexDirection: 'row',
    gap: spacing.md,
    marginTop: spacing.xl
  },
  metadataCard: { gap: spacing.md },
  metadataRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: spacing.md
  },
  metadataLabel: { color: colors.textSecondary, fontSize: 11 },
  metadataValue: { color: colors.text, fontSize: 11, fontWeight: '800' },
  actionGrid: { flexDirection: 'row', gap: spacing.md },
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
    width: 36,
    height: 36,
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
  modalActions: { flexDirection: 'row', gap: spacing.md, marginTop: spacing.xl }
});
