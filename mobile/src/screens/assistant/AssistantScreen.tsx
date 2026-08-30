import React, { useState } from 'react';
import {
  Alert,
  KeyboardAvoidingView,
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
import { Card } from '../../components/ui/Card';
import { PageTitle } from '../../components/ui/PageTitle';
import { Tag } from '../../components/ui/Tag';
import { useAppData } from '../../hooks/useAppData';
import { demoAnalyzePortfolio } from '../../utils/localCalculations';
import { colors, spacing } from '../../theme/theme';
import { formatCurrency } from '../../utils/formatting';

const prompts = [
  'Why is my portfolio risky?',
  'What is my biggest risk driver?',
  'Explain diversification in simple terms',
  'What happened in my last simulation?'
];

export function AssistantScreen() {
  const { activePortfolio } = useAppData();
  const [message, setMessage] = useState('');
  const [questions, setQuestions] = useState<string[]>([]);
  const analysis = activePortfolio ? demoAnalyzePortfolio(activePortfolio) : null;

  function send() {
    const trimmed = message.trim();
    if (!trimmed) return;
    setQuestions((current) => [...current, trimmed]);
    setMessage('');
    Alert.alert(
      'AI backend not connected',
      'The interface is ready, but Aura will not fabricate an AI response before the backend Agent is implemented.'
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView
          style={styles.flex}
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
        >
          <PageTitle
            eyebrow="AURA ASSISTANT"
            title="Ask Aura"
            subtitle="Ask questions about portfolio risk, analytics and simulations."
            right={<Tag label="UI READY" tone="primary" />}
          />

          {activePortfolio && analysis ? (
            <Card style={styles.contextCard}>
              <View style={styles.contextTop}>
                <View>
                  <Text style={styles.overline}>CURRENT CONTEXT</Text>
                  <Text style={styles.portfolio}>{activePortfolio.name}</Text>
                  <Text style={styles.value}>{formatCurrency(activePortfolio.totalValue)}</Text>
                </View>
                <View style={styles.scoreBadge}>
                  <Text style={styles.score}>{analysis.riskScore}</Text>
                  <Text style={styles.scoreOut}>/100</Text>
                </View>
              </View>

              <View style={styles.contextBottom}>
                <Text style={styles.contextStat}>{activePortfolio.holdings.length} Assets</Text>
                <Text style={styles.contextStat}>•</Text>
                <Text style={[styles.contextStat, { color: colors.warning }]}>
                  {analysis.diversification} Diversification
                </Text>
              </View>
            </Card>
          ) : null}

          <Text style={styles.sectionTitle}>Suggested questions</Text>
          <View style={styles.promptList}>
            {prompts.map((prompt) => (
              <Pressable
                key={prompt}
                onPress={() => setMessage(prompt)}
                style={styles.prompt}
              >
                <View style={styles.promptIcon}>
                  <Ionicons name="help-circle-outline" color={colors.primary} size={16} />
                </View>
                <Text style={styles.promptText}>{prompt}</Text>
                <Ionicons name="chevron-forward" color={colors.muted} size={18} />
              </Pressable>
            ))}
          </View>

          {questions.length ? (
            <>
              <Text style={styles.sectionTitle}>Conversation</Text>
              <View style={styles.conversation}>
                {questions.map((question, index) => (
                  <View key={`${question}-${index}`} style={styles.questionBlock}>
                    <View style={styles.userBubble}>
                      <Text style={styles.userText}>{question}</Text>
                    </View>
                    <View style={styles.pending}>
                      <Ionicons name="time-outline" size={13} color={colors.muted} />
                      <Text style={styles.pendingText}>Waiting for backend AI Agent</Text>
                    </View>
                  </View>
                ))}
              </View>
            </>
          ) : null}
        </ScrollView>

        <View style={styles.composerArea}>
          <View style={styles.composer}>
            <TextInput
              value={message}
              onChangeText={setMessage}
              placeholder="Ask something…"
              placeholderTextColor={colors.muted}
              style={styles.input}
              multiline
            />
            <Pressable
              disabled={!message.trim()}
              onPress={send}
              style={[styles.send, !message.trim() && { opacity: 0.35 }]}
            >
              <Ionicons name="arrow-up" color={colors.onPrimary} size={20} />
            </Pressable>
          </View>
          <Text style={styles.disclaimer}>Educational explanations only · Not financial advice</Text>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  flex: { flex: 1 },
  content: { padding: spacing.lg, paddingBottom: spacing.xl },
  contextCard: { marginTop: spacing.xl, gap: spacing.md },
  contextTop: { flexDirection: 'row', justifyContent: 'space-between', gap: spacing.md },
  overline: { color: colors.muted, fontSize: 9, fontWeight: '900', letterSpacing: 1.1 },
  portfolio: { color: colors.text, fontSize: 18, fontWeight: '900', marginTop: 5 },
  value: { color: colors.textSecondary, fontSize: 13, marginTop: 5 },
  scoreBadge: { width: 66, height: 66, borderRadius: 33, borderWidth: 2, borderColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  score: { color: colors.text, fontSize: 20, fontWeight: '900' },
  scoreOut: { color: colors.muted, fontSize: 9, marginTop: -2 },
  contextBottom: { flexDirection: 'row', gap: spacing.sm, paddingTop: spacing.md, borderTopWidth: 1, borderTopColor: colors.borderSoft },
  contextStat: { color: colors.textSecondary, fontSize: 11, fontWeight: '700' },
  sectionTitle: { color: colors.purpleSoft, fontSize: 11, fontWeight: '900', marginTop: spacing.xl, marginBottom: spacing.md },
  promptList: { gap: spacing.sm },
  prompt: { minHeight: 50, borderRadius: 14, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSoft, flexDirection: 'row', alignItems: 'center', gap: spacing.md, paddingHorizontal: spacing.md },
  promptIcon: { width: 30, height: 30, borderRadius: 10, backgroundColor: colors.cyanBackground, alignItems: 'center', justifyContent: 'center' },
  promptText: { color: colors.textSecondary, flex: 1, fontSize: 12, fontWeight: '700' },
  conversation: { gap: spacing.md },
  questionBlock: { alignItems: 'flex-end', gap: 6 },
  userBubble: { maxWidth: '84%', backgroundColor: colors.primary, borderRadius: 17, borderBottomRightRadius: 5, paddingHorizontal: 13, paddingVertical: 10 },
  userText: { color: colors.onPrimary, fontSize: 13, fontWeight: '800' },
  pending: { flexDirection: 'row', gap: 5, alignItems: 'center' },
  pendingText: { color: colors.muted, fontSize: 10 },
  composerArea: { padding: spacing.lg, paddingTop: spacing.md, backgroundColor: colors.background, borderTopWidth: 1, borderTopColor: colors.borderSoft },
  composer: { flexDirection: 'row', gap: spacing.sm, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: 18, padding: 7, alignItems: 'flex-end' },
  input: { flex: 1, minHeight: 40, maxHeight: 100, color: colors.text, paddingHorizontal: 8, paddingVertical: 9, fontSize: 13 },
  send: { width: 40, height: 40, borderRadius: 13, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  disclaimer: { color: colors.muted, textAlign: 'center', fontSize: 9, marginTop: 7 }
});
