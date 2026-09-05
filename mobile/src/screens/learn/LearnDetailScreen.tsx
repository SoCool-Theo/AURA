import React from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { learnLessons } from '../../mocks/learn.mock';
import { useAppData } from '../../hooks/useAppData';
import { colors, spacing, typography } from '../../theme/theme';

export function LearnDetailScreen({ route }: { route: any }) {
  const { learnProgress, toggleLessonComplete, localError, localPending, retryLocalData } = useAppData();
  const lesson = learnLessons.find((item) => item.id === route.params.lessonId);

  if (!lesson) {
    return (
      <SafeAreaView style={styles.safe}>
        <EmptyState
          title="Lesson not found"
          description="Return to Learn and choose another lesson."
        />
      </SafeAreaView>
    );
  }

  const done = Boolean(learnProgress[lesson.id]);

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.eyebrow}>{lesson.category.toUpperCase()}</Text>
        <Text style={styles.title}>{lesson.title}</Text>

        <View style={styles.metaRow}>
          <View style={styles.metaPill}>
            <Ionicons name="time-outline" size={14} color={colors.muted} />
            <Text style={styles.metaText}>{lesson.readMinutes} min read</Text>
          </View>
          {done ? (
            <View style={[styles.metaPill, styles.donePill]}>
              <Ionicons name="checkmark-circle" size={14} color={colors.success} />
              <Text style={[styles.metaText, { color: colors.success }]}>Completed</Text>
            </View>
          ) : null}
        </View>

        <Card style={styles.summaryCard}>
          <Text style={styles.summary}>{lesson.summary}</Text>
        </Card>

        <View style={styles.body}>
          {lesson.body.map((paragraph, index) => (
            <Text key={index} style={styles.paragraph}>
              {paragraph}
            </Text>
          ))}
        </View>

        <Card style={styles.noteCard}>
          <View style={styles.noteTop}>
            <Ionicons name="information-circle-outline" size={20} color={colors.primary} />
            <Text style={styles.noteTitle}>Aura learning boundary</Text>
          </View>
          <Text style={styles.noteText}>
            Learn explains the concepts shown in Aura. Production portfolio metrics and
            simulation results still come from the backend.
          </Text>
        </Card>

        {localError ? <Card><Text style={styles.noteText}>{localError}</Text><Button title="Retry local progress" onPress={() => void retryLocalData()} /></Card> : null}
        <Button
          title={done ? 'Mark as not completed' : 'Mark lesson completed'}
          variant={done ? 'secondary' : 'primary'}
          onPress={() => toggleLessonComplete(lesson.id)}
          disabled={localPending || Boolean(localError)}
          style={{ marginTop: spacing.xl }}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 100 },
  eyebrow: { color: colors.primary, fontSize: 10, fontWeight: '900', letterSpacing: 1.4 },
  title: { color: colors.text, ...typography.h1, marginTop: 5, lineHeight: 36 },
  metaRow: { flexDirection: 'row', gap: spacing.sm, marginTop: spacing.md, marginBottom: spacing.xl },
  metaPill: { flexDirection: 'row', alignItems: 'center', gap: 5, paddingHorizontal: 10, paddingVertical: 7, borderRadius: 999, backgroundColor: colors.surfaceAlt, borderWidth: 1, borderColor: colors.border },
  donePill: { borderColor: colors.successBorder },
  metaText: { color: colors.muted, fontSize: 11, fontWeight: '800' },
  summaryCard: { backgroundColor: colors.summaryBackground },
  summary: { color: colors.text, fontSize: 16, fontWeight: '800', lineHeight: 23 },
  body: { gap: spacing.lg, marginTop: spacing.xl },
  paragraph: { color: colors.textSecondary, fontSize: 15, lineHeight: 23 },
  noteCard: { marginTop: spacing.xl, gap: spacing.sm },
  noteTop: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  noteTitle: { color: colors.text, fontWeight: '900' },
  noteText: { color: colors.textSecondary, lineHeight: 20, fontSize: 13 }
});
