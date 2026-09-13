import { Ionicons } from '@expo/vector-icons';
import React, {
  useCallback,
  useEffect,
  useRef,
  useState
} from 'react';
import {
  StyleSheet,
  Text,
  TextInput,
  View
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { agentErrorMessage } from '../../agent/agentErrors';
import { agentApi } from '../../api/agentApi';
import { ApiError } from '../../api/apiClient';
import { PortfolioSelector } from '../../components/simulations/PortfolioSelector';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { FormErrorSummary, InlineErrorCard, ScreenErrorState } from '../../components/ui/ErrorState';
import { KeyboardAwareScrollView } from '../../components/ui/KeyboardAwareScrollView';
import { LoadingState } from '../../components/ui/LoadingState';
import { PageTitle } from '../../components/ui/PageTitle';
import { portfolioErrorMessage } from '../../portfolio/portfolioErrors';
import { usePortfolios } from '../../portfolio/usePortfolios';
import { colors, spacing } from '../../theme/theme';
import type {
  AgentExplainResponse,
  AgentSourceReference
} from '../../types/agent';

function sourceLabel(source: AgentSourceReference): string {
  return `${source.type.charAt(0).toUpperCase()}${source.type.slice(1)}`;
}

export function AssistantScreen({
  navigation,
  route
}: {
  navigation: any;
  route: any;
}) {
  const {
    portfolios,
    activePortfolioId,
    listStatus,
    listError,
    isRefreshing,
    refreshPortfolios,
    selectPortfolio
  } = usePortfolios();
  const [selectedPortfolioId, setSelectedPortfolioId] = useState('');
  const [message, setMessage] = useState('');
  const [response, setResponse] = useState<AgentExplainResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [requestFailure, setRequestFailure] = useState<unknown>(null);
  const [sending, setSending] = useState(false);
  const sendingRef = useRef(false);
  const requestVersionRef = useRef(0);
  const requestControllerRef = useRef<AbortController | null>(null);
  const requestedPortfolioId = route.params?.portfolioId as string | undefined;

  const cancelActiveRequest = useCallback(() => {
    requestVersionRef.current += 1;
    requestControllerRef.current?.abort();
    requestControllerRef.current = null;
    sendingRef.current = false;
    setSending(false);
  }, []);

  useEffect(() => () => {
    requestVersionRef.current += 1;
    requestControllerRef.current?.abort();
    requestControllerRef.current = null;
    sendingRef.current = false;
  }, []);

  useEffect(() => {
    if (listStatus !== 'ready' && !portfolios.length) return;
    if (
      requestedPortfolioId
      && portfolios.some((item) => item.id === requestedPortfolioId)
    ) {
      navigation.setParams({ portfolioId: undefined });
      if (requestedPortfolioId === selectedPortfolioId) return;
      cancelActiveRequest();
      setSelectedPortfolioId(requestedPortfolioId);
      selectPortfolio(requestedPortfolioId);
      setResponse(null);
      setError(null);
      setRequestFailure(null);
      return;
    }
    if (requestedPortfolioId) {
      navigation.setParams({ portfolioId: undefined });
    }
    if (portfolios.some((item) => item.id === selectedPortfolioId)) return;

    const nextPortfolioId = (
      activePortfolioId
      && portfolios.some((item) => item.id === activePortfolioId)
    ) ? activePortfolioId : portfolios[0]?.id ?? '';

    cancelActiveRequest();
    setSelectedPortfolioId(nextPortfolioId);
    setResponse(null);
    setError(null);
    setRequestFailure(null);
    if (nextPortfolioId && nextPortfolioId !== activePortfolioId) {
      selectPortfolio(nextPortfolioId);
    }
  }, [
    activePortfolioId,
    cancelActiveRequest,
    listStatus,
    navigation,
    portfolios,
    requestedPortfolioId,
    selectPortfolio,
    selectedPortfolioId
  ]);

  function choosePortfolio(portfolioId: string) {
    if (portfolioId === selectedPortfolioId || sendingRef.current) return;
    cancelActiveRequest();
    setSelectedPortfolioId(portfolioId);
    selectPortfolio(portfolioId);
    setResponse(null);
    setError(null);
    setRequestFailure(null);
  }

  function editMessage(value: string) {
    setMessage(value);
    setResponse(null);
    setError(null);
    setRequestFailure(null);
  }

  async function askAura() {
    if (sendingRef.current) return;
    const normalizedMessage = message.trim();
    if (!selectedPortfolioId) {
      setRequestFailure(null);
      setError('Choose a portfolio before asking Aura a question.');
      return;
    }
    if (!normalizedMessage) {
      setRequestFailure(null);
      setError('Enter a question for Aura.');
      return;
    }
    if (normalizedMessage.length > 4000) {
      setRequestFailure(null);
      setError('Questions must contain no more than 4,000 characters.');
      return;
    }

    const requestId = requestVersionRef.current + 1;
    requestVersionRef.current = requestId;
    const controller = new AbortController();
    requestControllerRef.current = controller;
    sendingRef.current = true;
    setSending(true);
    setError(null);
    setRequestFailure(null);
    setResponse(null);

    try {
      const result = await agentApi.explain(
        {
          portfolio_id: selectedPortfolioId,
          message: normalizedMessage
        },
        { signal: controller.signal }
      );
      if (controller.signal.aborted || requestVersionRef.current !== requestId) {
        return;
      }
      setResponse(result);
    } catch (requestError) {
      if (controller.signal.aborted || requestVersionRef.current !== requestId) {
        return;
      }
      setError(agentErrorMessage(requestError));
      setRequestFailure(requestError);
      if (requestError instanceof ApiError && requestError.status === 404) {
        void refreshPortfolios();
      }
    } finally {
      if (requestVersionRef.current === requestId) {
        requestControllerRef.current = null;
        sendingRef.current = false;
        setSending(false);
      }
    }
  }

  if (
    (listStatus === 'idle' || listStatus === 'loading')
    && !portfolios.length
  ) {
    return <LoadingState message="Loading portfolios for Aura…" />;
  }

  if (listStatus === 'error' && !portfolios.length) {
    return (
      <SafeAreaView style={styles.safe} edges={['bottom']}>
        <ScreenErrorState
          error={listError}
          resourceName="Portfolio list"
          fallbackMessage="Unable to load portfolios for Aura."
          onRetry={() => void refreshPortfolios()}
          retryTitle={isRefreshing ? 'Retrying…' : 'Retry'}
        />
      </SafeAreaView>
    );
  }

  if (listStatus === 'ready' && !portfolios.length) {
    return (
      <SafeAreaView style={styles.safe} edges={['bottom']}>
        <View style={styles.centerState}>
          <Card>
            <EmptyState
              icon="sparkles-outline"
              title="Create a portfolio first"
              description="Aura needs a saved backend portfolio before it can provide a grounded explanation."
            />
            <Button
              title="Create Portfolio"
              onPress={() => navigation.navigate('Portfolio', {
                screen: 'CreatePortfolio'
              })}
            />
          </Card>
        </View>
      </SafeAreaView>
    );
  }

  const selectedPortfolio = portfolios.find((item) => item.id === selectedPortfolioId);

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <KeyboardAwareScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
      >
        <PageTitle
          eyebrow="GROUNDED PORTFOLIO EXPLANATIONS"
          title="Ask Aura"
          subtitle="Understand backend-calculated portfolio risk in plain language."
        />

        <Card style={styles.safetyCard}>
          <View style={styles.safetyIcon}>
            <Ionicons
              name="shield-checkmark-outline"
              color={colors.primary}
              size={22}
            />
          </View>
          <View style={styles.safetyCopy}>
            <Text style={styles.safetyTitle}>Educational explanations only</Text>
            <Text style={styles.body}>
              Aura explains stored results. It does not calculate, predict, or recommend investments.
            </Text>
          </View>
        </Card>

        {listStatus === 'error' ? (
          <InlineErrorCard
            error={listError}
            message={portfolioErrorMessage(listError)}
            stale
            onRetry={() => void refreshPortfolios()}
            retryTitle={isRefreshing ? 'Retrying…' : 'Retry portfolios'}
          />
        ) : null}

        <Card style={styles.askCard}>
          <View>
            <Text style={styles.fieldLabel}>Portfolio</Text>
            <PortfolioSelector
              portfolios={portfolios}
              selectedId={selectedPortfolioId || null}
              disabled={sending}
              onSelect={choosePortfolio}
            />
          </View>

          <View>
            <View style={styles.questionHeader}>
              <Text style={styles.fieldLabel}>Your question</Text>
              <Text style={styles.counter}>{message.length}/4000</Text>
            </View>
            <TextInput
              accessibilityLabel="Question for Aura"
              accessibilityState={{ disabled: sending }}
              value={message}
              onChangeText={editMessage}
              placeholder="For example: What are the main risk factors in this portfolio?"
              placeholderTextColor={colors.muted}
              multiline
              maxLength={4000}
              editable={!sending}
              textAlignVertical="top"
              style={styles.questionInput}
            />
          </View>

          <Text style={styles.contextNote}>
            The backend uses {selectedPortfolio?.portfolio_type === 'PLANNED'
              ? 'this hypothetical plan, its proposed-amount target allocation,'
              : 'this portfolio'} and its newest saved report when available. No financial calculations run on this device.
          </Text>
          <Button
            title={sending ? 'Asking Aura…' : 'Ask Aura'}
            disabled={sending || !selectedPortfolioId || !message.trim()}
            onPress={() => void askAura()}
          />
        </Card>

        {error ? (
          <FormErrorSummary error={requestFailure} message={error} title="Explanation unavailable" />
        ) : null}

        {sending ? (
          <Card style={styles.statusCard}>
            <Ionicons name="sparkles-outline" color={colors.primary} size={24} />
            <View style={styles.statusCopy}>
              <Text style={styles.statusTitle}>Aura is preparing an explanation</Text>
              <Text style={styles.body}>
                Using backend-owned portfolio and saved-report context.
              </Text>
            </View>
          </Card>
        ) : null}

        {response && !sending ? (
          <View style={styles.responseSection}>
            <Card style={styles.answerCard}>
              <View style={styles.answerHeading}>
                <View style={styles.answerIcon}>
                  <Ionicons name="sparkles" color={colors.primary} size={20} />
                </View>
                <View style={styles.answerTitleGroup}>
                  <Text style={styles.answerEyebrow}>AURA’S EXPLANATION</Text>
                  <Text style={styles.answerTitle}>Grounded response</Text>
                </View>
              </View>
              <Text selectable style={styles.answerText}>{response.answer}</Text>
            </Card>

            <Card style={styles.detailCard}>
              <Text style={styles.detailTitle}>Sources</Text>
              {response.sources.length ? response.sources.map((source) => (
                <View key={`${source.type}-${source.id}`} style={styles.sourceRow}>
                  <Text style={styles.sourceType}>{sourceLabel(source)}</Text>
                  <Text selectable style={styles.sourceId}>{source.id}</Text>
                </View>
              )) : (
                <Text style={styles.body}>
                  No stored source references were required for this response.
                </Text>
              )}
            </Card>

            <Card style={styles.detailCard}>
              <Text style={styles.detailTitle}>Limitations</Text>
              {response.limitations.length ? response.limitations.map((limitation) => (
                <View key={limitation} style={styles.limitationRow}>
                  <Text style={styles.bullet}>•</Text>
                  <Text style={styles.limitationText}>{limitation}</Text>
                </View>
              )) : (
                <Text style={styles.body}>No additional limitations were returned.</Text>
              )}
            </Card>
          </View>
        ) : null}
      </KeyboardAwareScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: {
    padding: spacing.lg,
    paddingBottom: 110,
    gap: spacing.md
  },
  centerState: { flex: 1, justifyContent: 'center', padding: spacing.xl },
  safetyCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    marginTop: spacing.md,
    backgroundColor: colors.selectedBackground,
    borderColor: colors.primary
  },
  safetyIcon: {
    width: 42,
    height: 42,
    borderRadius: 13,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.surface
  },
  safetyCopy: { flex: 1, gap: 3 },
  safetyTitle: { color: colors.text, fontSize: 13, fontWeight: '900' },
  body: { color: colors.textSecondary, fontSize: 12, lineHeight: 18 },
  askCard: { gap: spacing.md },
  fieldLabel: {
    color: colors.text,
    fontSize: 12,
    fontWeight: '900',
    marginBottom: spacing.sm
  },
  questionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  counter: { color: colors.muted, fontSize: 10 },
  questionInput: {
    minHeight: 132,
    borderRadius: 15,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceAlt,
    color: colors.text,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    fontSize: 14,
    lineHeight: 20
  },
  contextNote: { color: colors.muted, fontSize: 10, lineHeight: 16 },
  errorCard: { gap: spacing.md, borderColor: colors.dangerBorder },
  errorTitle: { color: colors.danger, fontSize: 15, fontWeight: '900' },
  statusCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md
  },
  statusCopy: { flex: 1, gap: 3 },
  statusTitle: { color: colors.text, fontSize: 14, fontWeight: '900' },
  responseSection: { gap: spacing.md },
  answerCard: { gap: spacing.md, borderColor: colors.primary },
  answerHeading: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  answerIcon: {
    width: 42,
    height: 42,
    borderRadius: 13,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.selectedBackground
  },
  answerTitleGroup: { flex: 1 },
  answerEyebrow: { color: colors.primary, fontSize: 9, fontWeight: '900' },
  answerTitle: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '900',
    marginTop: 2
  },
  answerText: { color: colors.text, fontSize: 14, lineHeight: 22 },
  detailCard: { gap: spacing.sm },
  detailTitle: { color: colors.text, fontSize: 14, fontWeight: '900' },
  sourceRow: {
    borderTopWidth: 1,
    borderTopColor: colors.borderSoft,
    paddingTop: spacing.sm,
    gap: 3
  },
  sourceType: { color: colors.primary, fontSize: 11, fontWeight: '900' },
  sourceId: { color: colors.muted, fontSize: 9 },
  limitationRow: { flexDirection: 'row', gap: spacing.sm },
  bullet: { color: colors.primary, fontSize: 15 },
  limitationText: {
    flex: 1,
    color: colors.textSecondary,
    fontSize: 12,
    lineHeight: 18
  }
});
