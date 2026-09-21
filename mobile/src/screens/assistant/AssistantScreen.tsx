import { Ionicons } from '@expo/vector-icons';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { agentErrorMessage } from '../../agent/agentErrors';
import { agentApi } from '../../api/agentApi';
import { ApiError } from '../../api/apiClient';
import { AnswerContent } from '../../components/assistant/AnswerContent';
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
  AgentConversationMessage,
  AgentExplainResponse,
  AgentSourceReference
} from '../../types/agent';

type ChatMessage =
  | { id: number; role: 'user'; content: string }
  | {
    id: number;
    role: 'assistant';
    content: string;
    response: AgentExplainResponse;
  };

const CURRENT_STARTER_QUESTIONS = [
  'What is my portfolio?',
  'Explain my portfolio risk simply.',
  'What are the main risks?',
  'What are the advantages and disadvantages?'
] as const;

const PLANNED_STARTER_QUESTIONS = [
  'What does this planned portfolio look like?',
  'Explain this planned allocation simply.',
  'What are the main risks of this plan?',
  'Why is this planned allocation concentrated?'
] as const;

const FOLLOW_UP_QUESTIONS = [
  'Explain that more simply.',
  'Why does that matter?',
  'Which number should I pay attention to most?'
] as const;

function sourceLabel(source: AgentSourceReference): string {
  return `${source.type.charAt(0).toUpperCase()}${source.type.slice(1)}`;
}

export function AssistantScreen({ navigation, route }: { navigation: any; route: any }) {
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
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [expandedMessageIds, setExpandedMessageIds] = useState<number[]>([]);
  const [composerHeight, setComposerHeight] = useState(0);
  const [composerHidden, setComposerHidden] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [requestFailure, setRequestFailure] = useState<unknown>(null);
  const [sending, setSending] = useState(false);
  const sendingRef = useRef(false);
  const nextMessageIdRef = useRef(1);
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

  const resetConversation = useCallback(() => {
    setMessages([]);
    setExpandedMessageIds([]);
    setComposerHidden(false);
    setMessage('');
    setError(null);
    setRequestFailure(null);
  }, []);

  useEffect(() => () => {
    requestVersionRef.current += 1;
    requestControllerRef.current?.abort();
    requestControllerRef.current = null;
    sendingRef.current = false;
  }, []);

  useEffect(() => {
    if (listStatus !== 'ready' && !portfolios.length) return;
    if (requestedPortfolioId && portfolios.some((item) => item.id === requestedPortfolioId)) {
      navigation.setParams({ portfolioId: undefined });
      if (requestedPortfolioId === selectedPortfolioId) return;
      cancelActiveRequest();
      setSelectedPortfolioId(requestedPortfolioId);
      selectPortfolio(requestedPortfolioId);
      resetConversation();
      return;
    }
    if (requestedPortfolioId) navigation.setParams({ portfolioId: undefined });
    if (portfolios.some((item) => item.id === selectedPortfolioId)) return;

    const nextPortfolioId = (
      activePortfolioId && portfolios.some((item) => item.id === activePortfolioId)
    ) ? activePortfolioId : portfolios[0]?.id ?? '';

    cancelActiveRequest();
    setSelectedPortfolioId(nextPortfolioId);
    resetConversation();
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
    resetConversation,
    selectPortfolio,
    selectedPortfolioId
  ]);

  function choosePortfolio(portfolioId: string) {
    if (portfolioId === selectedPortfolioId || sendingRef.current) return;
    cancelActiveRequest();
    setSelectedPortfolioId(portfolioId);
    selectPortfolio(portfolioId);
    resetConversation();
  }

  function editMessage(value: string) {
    setMessage(value);
    setError(null);
    setRequestFailure(null);
  }

  function chooseQuestion(question: string) {
    if (sendingRef.current || !selectedPortfolioId) return;
    setComposerHidden(false);
    editMessage(question);
  }

  function startNewChat() {
    if (!sendingRef.current) resetConversation();
  }

  function toggleGrounding(messageId: number) {
    setExpandedMessageIds((current) => current.includes(messageId)
      ? current.filter((id) => id !== messageId)
      : [...current, messageId]);
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

    const history: AgentConversationMessage[] = messages.slice(-8).map((item) => ({
      role: item.role,
      content: item.content
    }));
    const userMessage: ChatMessage = {
      id: nextMessageIdRef.current++,
      role: 'user',
      content: normalizedMessage
    };
    const requestId = requestVersionRef.current + 1;
    requestVersionRef.current = requestId;
    const controller = new AbortController();
    requestControllerRef.current = controller;
    sendingRef.current = true;
    setSending(true);
    setError(null);
    setRequestFailure(null);
    setMessages((current) => [...current, userMessage]);
    setMessage('');

    try {
      const result = await agentApi.explain(
        { portfolio_id: selectedPortfolioId, message: normalizedMessage, history },
        { signal: controller.signal }
      );
      if (controller.signal.aborted || requestVersionRef.current !== requestId) return;
      setMessages((current) => [...current, {
        id: nextMessageIdRef.current++,
        role: 'assistant',
        content: result.answer,
        response: result
      }]);
    } catch (requestError) {
      if (controller.signal.aborted || requestVersionRef.current !== requestId) return;
      setMessages((current) => current.filter((item) => item.id !== userMessage.id));
      setMessage(normalizedMessage);
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

  if ((listStatus === 'idle' || listStatus === 'loading') && !portfolios.length) {
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
              description="Create and save a portfolio before asking Aura about its risk."
            />
            <Button
              title="Create Portfolio"
              onPress={() => navigation.navigate('Portfolio', { screen: 'CreatePortfolio' })}
            />
          </Card>
        </View>
      </SafeAreaView>
    );
  }

  const selectedPortfolio = portfolios.find((item) => item.id === selectedPortfolioId);
  const isPlanned = selectedPortfolio?.portfolio_type === 'PLANNED';
  const isLegacy = selectedPortfolio?.portfolio_type === 'LEGACY';
  const starterQuestions = isPlanned ? PLANNED_STARTER_QUESTIONS : CURRENT_STARTER_QUESTIONS;
  const contextTitle = isPlanned
    ? 'Planned portfolio context'
    : isLegacy ? 'Legacy allocation context' : 'Current portfolio context';
  const contextDescription = isPlanned
    ? 'Aura explains this proposed allocation as hypothetical—not as assets you already own—and uses its newest saved report when available.'
    : isLegacy
      ? 'Aura explains the portfolio’s saved compatibility allocation and its newest saved report when available.'
      : 'Aura explains the current allocation derived from your saved holdings and its newest saved report when available.';
  const latestAssistantMessageId = messages.reduce<number | null>(
    (latestId, item) => item.role === 'assistant' ? item.id : latestId,
    null
  );
  const composer = (
    <View
      onLayout={({ nativeEvent }) => setComposerHeight(nativeEvent.layout.height)}
      style={[styles.composerDock, composerHidden && styles.composerDockHidden]}
    >
      {composerHidden ? (
        <Pressable
          accessibilityLabel="Show message composer"
          accessibilityRole="button"
          onPress={() => setComposerHidden(false)}
          style={({ pressed }) => [styles.showComposerButton, pressed && styles.pressed]}
        >
          <Ionicons name="chevron-up" color={colors.primary} size={22} />
        </Pressable>
      ) : (
      <Card style={styles.composerCard}>
        <View style={styles.questionHeader}>
          <Text style={styles.fieldLabel}>Your question</Text>
          <View style={styles.questionHeaderActions}>
            <Text style={styles.counter}>{message.length}/4000</Text>
            <Pressable
              accessibilityLabel="Hide message composer"
              accessibilityRole="button"
              onPress={() => setComposerHidden(true)}
              style={({ pressed }) => [styles.hideComposerButton, pressed && styles.pressed]}
            >
              <Ionicons name="chevron-down" color={colors.textSecondary} size={20} />
            </Pressable>
          </View>
        </View>
        <TextInput
          accessibilityLabel="Question for Aura"
          accessibilityState={{ disabled: sending }}
          value={message}
          onChangeText={editMessage}
          placeholder={isPlanned ? 'Ask about this proposed allocation…' : 'Ask about this portfolio…'}
          placeholderTextColor={colors.muted}
          multiline
          maxLength={4000}
          editable={!sending}
          textAlignVertical="top"
          style={styles.questionInput}
        />
        <View style={styles.actionRow}>
          {messages.length ? (
            <Button
              title="New chat"
              variant="ghost"
              disabled={sending}
              onPress={startNewChat}
              style={styles.newChatButton}
            />
          ) : <View />}
          <Button
            title={sending ? 'Asking Aura…' : 'Send'}
            disabled={sending || !selectedPortfolioId || !message.trim()}
            onPress={() => void askAura()}
            style={styles.sendButton}
          />
        </View>
        <View style={styles.composerMeta}>
          <Ionicons name="shield-checkmark-outline" color={colors.muted} size={13} />
          <Text style={styles.composerMetaText}>Educational explanations only</Text>
        </View>
      </Card>
      )}
    </View>
  );

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <KeyboardAwareScrollView
        contentContainerStyle={[
          styles.content,
          { paddingBottom: composerHeight + spacing.lg }
        ]}
        footer={composer}
        keyboardShouldPersistTaps="handled"
      >
        <PageTitle
          eyebrow="GROUNDED PORTFOLIO EXPLANATIONS"
          title="Ask Aura"
          subtitle="Ask follow-up questions while Aura grounds every answer in your portfolio data."
        />

        <View style={styles.safetyNote}>
          <Ionicons name="shield-checkmark-outline" color={colors.primary} size={18} />
          <Text style={styles.safetyText}>Educational explanations only</Text>
        </View>

        {listStatus === 'error' ? (
          <InlineErrorCard
            error={listError}
            message={portfolioErrorMessage(listError)}
            stale
            onRetry={() => void refreshPortfolios()}
            retryTitle={isRefreshing ? 'Retrying…' : 'Retry portfolios'}
          />
        ) : null}

        <Card style={styles.contextPanel}>
          <View>
            <Text style={styles.fieldLabel}>Portfolio</Text>
            <PortfolioSelector
              portfolios={portfolios}
              selectedId={selectedPortfolioId || null}
              disabled={sending}
              onSelect={choosePortfolio}
            />
          </View>
          {selectedPortfolio ? (
            <View style={[styles.contextCard, isPlanned && styles.plannedContextCard]}>
              <Text style={styles.contextEyebrow}>LIVE PORTFOLIO</Text>
              <Text style={styles.contextTitle}>{contextTitle}</Text>
              <Text style={styles.contextDescription}>{contextDescription}</Text>
            </View>
          ) : null}
        </Card>

        <View accessibilityLiveRegion="polite" style={styles.chatSection}>
          {!messages.length && !sending ? (
            <Card style={styles.emptyChat}>
              <View style={styles.emptyChatIcon}>
                <Ionicons name="sparkles" color={colors.primary} size={21} />
              </View>
              <View style={styles.emptyChatContent}>
                <Text style={styles.emptyChatTitle}>Start a conversation</Text>
                <Text style={styles.body}>
                  Ask about holdings, risk, historical performance, or diversification.
                </Text>
                <Text style={styles.suggestionLabel}>TRY ASKING</Text>
                <View style={styles.questionChips}>
                  {starterQuestions.map((question) => (
                    <Pressable
                      accessibilityRole="button"
                      key={question}
                      onPress={() => chooseQuestion(question)}
                      style={({ pressed }) => [styles.questionChip, pressed && styles.pressed]}
                    >
                      <Text style={styles.questionChipText}>{question}</Text>
                    </Pressable>
                  ))}
                </View>
              </View>
            </Card>
          ) : null}

          {messages.map((item) => item.role === 'user' ? (
            <View key={item.id} style={styles.userRow}>
              <View style={styles.userBubble}>
                <Text style={styles.messageEyebrow}>YOU</Text>
                <Text selectable style={styles.userMessage}>{item.content}</Text>
              </View>
            </View>
          ) : (
            <View key={item.id} style={styles.assistantRow}>
              <View style={styles.assistantAvatar}>
                <Ionicons name="sparkles" color={colors.primary} size={17} />
              </View>
              <View style={styles.assistantMessageColumn}>
                <Card style={styles.assistantBubble}>
                  <Text style={styles.messageEyebrow}>AURA</Text>
                  <AnswerContent answer={item.content} />
                  {item.response.sources.length || item.response.limitations.length ? (
                    <View style={styles.groundingSection}>
                      <Pressable
                        accessibilityRole="button"
                        accessibilityState={{ expanded: expandedMessageIds.includes(item.id) }}
                        onPress={() => toggleGrounding(item.id)}
                        style={styles.groundingToggle}
                      >
                        <Text style={styles.groundingToggleText}>Grounding details</Text>
                        <Ionicons
                          name={expandedMessageIds.includes(item.id) ? 'chevron-up' : 'chevron-down'}
                          color={colors.textSecondary}
                          size={16}
                        />
                      </Pressable>
                      {expandedMessageIds.includes(item.id) ? (
                        <View style={styles.groundingContent}>
                          {item.response.sources.length ? (
                            <View style={styles.groundingGroup}>
                              <Text style={styles.groundingTitle}>Sources</Text>
                              {item.response.sources.map((source) => (
                                <Text selectable key={`${item.id}-${source.type}-${source.id}`} style={styles.groundingText}>
                                  • {sourceLabel(source)} · {source.id}
                                </Text>
                              ))}
                            </View>
                          ) : null}
                          {item.response.limitations.length ? (
                            <View style={styles.groundingGroup}>
                              <Text style={styles.groundingTitle}>Limitations</Text>
                              {item.response.limitations.map((limitation) => (
                                <Text key={`${item.id}-${limitation}`} style={styles.groundingText}>
                                  • {limitation}
                                </Text>
                              ))}
                            </View>
                          ) : null}
                        </View>
                      ) : null}
                    </View>
                  ) : null}
                </Card>
                {item.id === latestAssistantMessageId && !sending ? (
                  <View style={styles.followUpSection}>
                    <Text style={[styles.suggestionLabel, styles.followUpLabel]}>FOLLOW-UP IDEAS</Text>
                    <View style={styles.followUpChips}>
                      {FOLLOW_UP_QUESTIONS.map((question) => (
                        <Pressable
                          accessibilityRole="button"
                          key={question}
                          onPress={() => chooseQuestion(question)}
                          style={({ pressed }) => [styles.followUpChip, pressed && styles.pressed]}
                        >
                          <Text style={styles.followUpChipText}>{question}</Text>
                        </Pressable>
                      ))}
                    </View>
                  </View>
                ) : null}
              </View>
            </View>
          ))}

          {sending ? (
            <View style={styles.assistantRow}>
              <View style={styles.assistantAvatar}>
                <Ionicons name="sparkles" color={colors.primary} size={17} />
              </View>
              <Card style={styles.assistantBubble}>
                <Text style={styles.messageEyebrow}>AURA</Text>
                <Text style={styles.typingText}>Thinking about your portfolio context…</Text>
              </Card>
            </View>
          ) : null}
        </View>

        {error ? (
          <FormErrorSummary error={requestFailure} message={error} title="Explanation unavailable" />
        ) : null}

      </KeyboardAwareScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, gap: spacing.md },
  centerState: { flex: 1, justifyContent: 'center', padding: spacing.xl },
  safetyNote: {
    alignSelf: 'flex-start', flexDirection: 'row', alignItems: 'center', gap: spacing.sm,
    borderWidth: 1, borderColor: colors.border, borderRadius: 12,
    backgroundColor: colors.surfaceAlt, paddingHorizontal: spacing.md, paddingVertical: 10
  },
  safetyText: { color: colors.primary, fontSize: 11, fontWeight: '800' },
  body: { color: colors.textSecondary, fontSize: 12, lineHeight: 19 },
  contextPanel: { gap: spacing.md },
  fieldLabel: { color: colors.text, fontSize: 12, fontWeight: '900', marginBottom: spacing.sm },
  contextCard: {
    borderWidth: 1, borderColor: colors.successBorder, borderRadius: 12,
    backgroundColor: colors.selectedBackground, padding: spacing.md, gap: 4
  },
  plannedContextCard: { borderColor: colors.purple, backgroundColor: colors.purpleBackground },
  contextEyebrow: { color: colors.primary, fontSize: 9, fontWeight: '900', letterSpacing: 1 },
  contextTitle: { color: colors.text, fontSize: 13, fontWeight: '900' },
  contextDescription: { color: colors.textSecondary, fontSize: 11, lineHeight: 17 },
  chatSection: { gap: spacing.md },
  emptyChat: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.md },
  emptyChatIcon: {
    width: 40, height: 40, borderRadius: 12, alignItems: 'center', justifyContent: 'center',
    backgroundColor: colors.selectedBackground
  },
  emptyChatContent: { flex: 1, gap: spacing.xs },
  emptyChatTitle: { color: colors.text, fontSize: 17, fontWeight: '900' },
  suggestionLabel: {
    color: colors.muted, fontSize: 9, fontWeight: '900', letterSpacing: 1, marginTop: spacing.md
  },
  questionChips: { gap: spacing.sm, marginTop: spacing.xs },
  questionChip: {
    minHeight: 42, justifyContent: 'center', borderWidth: 1, borderColor: colors.border,
    borderRadius: 11, backgroundColor: colors.surfaceAlt,
    paddingHorizontal: spacing.md, paddingVertical: spacing.sm
  },
  questionChipText: { color: colors.textSecondary, fontSize: 11, lineHeight: 16 },
  userRow: { alignItems: 'flex-end', paddingLeft: 52 },
  userBubble: {
    maxWidth: '90%', borderWidth: 1, borderColor: colors.successBorder, borderRadius: 17,
    borderBottomRightRadius: 5, backgroundColor: colors.selectedBackground,
    paddingHorizontal: 14, paddingVertical: 12, gap: 4
  },
  messageEyebrow: { color: colors.primary, fontSize: 9, fontWeight: '900', letterSpacing: 1 },
  userMessage: { color: colors.text, fontSize: 13, lineHeight: 20 },
  assistantRow: {
    flexDirection: 'row', alignItems: 'flex-start', gap: 10, paddingRight: spacing.md
  },
  assistantAvatar: {
    width: 34, height: 34, borderRadius: 10, alignItems: 'center', justifyContent: 'center',
    backgroundColor: colors.selectedBackground, marginTop: 2
  },
  assistantMessageColumn: { flex: 1, gap: spacing.sm },
  assistantBubble: { borderTopLeftRadius: 5, gap: spacing.sm },
  typingText: { color: colors.muted, fontSize: 12, lineHeight: 18 },
  groundingSection: {
    marginTop: spacing.xs, paddingTop: spacing.sm,
    borderTopWidth: 1, borderTopColor: colors.borderSoft
  },
  groundingToggle: {
    minHeight: 34, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between'
  },
  groundingToggleText: { color: colors.textSecondary, fontSize: 11, fontWeight: '800' },
  groundingContent: { gap: spacing.md, paddingTop: spacing.sm },
  groundingGroup: { gap: spacing.xs },
  groundingTitle: { color: colors.text, fontSize: 11, fontWeight: '900' },
  groundingText: { color: colors.muted, fontSize: 9, lineHeight: 15 },
  composerDock: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
    paddingBottom: spacing.sm
  },
  composerDockHidden: { alignItems: 'flex-end' },
  composerCard: { gap: spacing.md },
  followUpSection: { gap: spacing.sm },
  followUpLabel: { marginTop: 0 },
  followUpChips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  followUpChip: {
    borderWidth: 1, borderColor: colors.border, borderRadius: 999,
    paddingHorizontal: 10, paddingVertical: 7
  },
  followUpChipText: { color: colors.textSecondary, fontSize: 10 },
  questionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  questionHeaderActions: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  hideComposerButton: {
    width: 32,
    height: 32,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.surfaceAlt
  },
  showComposerButton: {
    width: 46,
    height: 42,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface
  },
  counter: { color: colors.muted, fontSize: 10 },
  questionInput: {
    minHeight: 96, borderRadius: 12, borderWidth: 1, borderColor: colors.border,
    backgroundColor: colors.surfaceAlt, color: colors.text,
    paddingHorizontal: spacing.md, paddingVertical: spacing.md, fontSize: 13, lineHeight: 20
  },
  actionRow: {
    minHeight: 48, flexDirection: 'row', alignItems: 'center',
    justifyContent: 'space-between', gap: spacing.md
  },
  newChatButton: { minWidth: 96 },
  sendButton: { minWidth: 112 },
  composerMeta: {
    flexDirection: 'row', justifyContent: 'flex-end', alignItems: 'center', gap: 5
  },
  composerMetaText: { color: colors.muted, fontSize: 9 },
  pressed: { opacity: 0.72 }
});
