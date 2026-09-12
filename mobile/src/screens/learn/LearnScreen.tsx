import React, { useMemo, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { KeyboardAwareScrollView } from '../../components/ui/KeyboardAwareScrollView';
import { PageTitle } from '../../components/ui/PageTitle';
import { Tag } from '../../components/ui/Tag';
import { learnLessons } from '../../mocks/learn.mock';
import { useAppData } from '../../hooks/useAppData';
import { colors, spacing } from '../../theme/theme';

const categories = ['All', 'Risk Basics', 'Analytics', 'Simulation', 'AI'] as const;

export function LearnScreen({ navigation }: { navigation: any }) {
  const { learnProgress, localError, retryLocalData } = useAppData();
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState<(typeof categories)[number]>('All');

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return learnLessons.filter((lesson) => {
      const categoryMatch =
        category === 'All' ||
        lesson.category === category ||
        (category === 'Risk Basics' && lesson.category === 'Portfolio');
      const queryMatch =
        !normalized ||
        lesson.title.toLowerCase().includes(normalized) ||
        lesson.summary.toLowerCase().includes(normalized);
      return categoryMatch && queryMatch;
    });
  }, [query, category]);

  const completed = learnLessons.filter((lesson) => learnProgress[lesson.id]).length;
  const progress = Math.round((completed / learnLessons.length) * 100);

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <KeyboardAwareScrollView contentContainerStyle={styles.content}>
        <PageTitle title="Learn" subtitle="Static educational lessons. Progress is saved on this device only." />
        {localError ? <Card><Text style={styles.progressLabel}>{localError}</Text><Button title="Retry local progress" onPress={() => void retryLocalData()} /></Card> : null}

        <Card style={styles.progressCard}>
          <View style={styles.progressTop}>
            <View>
              <Text style={styles.overline}>YOUR PROGRESS</Text>
              <Text style={styles.progressCount}>{completed}/{learnLessons.length}</Text>
              <Text style={styles.progressLabel}>Lessons completed</Text>
            </View>
            <View style={styles.bulb}>
              <Ionicons name="bulb-outline" color={colors.purpleSoft} size={32} />
            </View>
          </View>
          <View style={styles.track}>
            <View style={[styles.fill, { width: `${progress}%` }]} />
          </View>
        </Card>

        <Input accessibilityLabel="Search lessons" value={query} onChangeText={setQuery} placeholder="Search lessons…" />

        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.filters}
        >
          {categories.map((item) => (
            <Pressable
              accessibilityLabel={`${item} lesson category`}
              accessibilityRole="radio"
              accessibilityState={{ selected: category === item }}
              key={item}
              onPress={() => setCategory(item)}
              style={styles.filterOption}
            >
              <Tag label={item} tone={category === item ? 'primary' : 'default'} />
            </Pressable>
          ))}
        </ScrollView>

        <View style={styles.list}>
          {filtered.map((lesson, index) => {
            const done = Boolean(learnProgress[lesson.id]);
            const tones = [
              { bg: colors.positiveBackground, fg: colors.success },
              { bg: colors.cyanBackground, fg: colors.primary },
              { bg: colors.blueBackground, fg: colors.blue },
              { bg: colors.warningBackground, fg: colors.warning }
            ];
            const tone = tones[index % tones.length];

            return (
              <Pressable
                accessibilityLabel={`Open ${lesson.title} lesson${done ? ', completed' : ''}`}
                accessibilityRole="button"
                key={lesson.id}
                onPress={() => navigation.navigate('LearnDetail', { lessonId: lesson.id })}
              >
                <Card style={styles.lessonCard}>
                  <View style={[styles.lessonIcon, { backgroundColor: tone.bg }]}>
                    <Ionicons
                      name={done ? 'checkmark' : 'book-outline'}
                      color={tone.fg}
                      size={21}
                    />
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.lessonTitle}>{lesson.title}</Text>
                    <Text style={styles.lessonMeta}>
                      {lesson.readMinutes} min · {lesson.category}
                    </Text>
                  </View>
                  <View style={styles.lessonRight}>
                    <Text style={[styles.completion, { color: done ? colors.success : colors.muted }]}>
                      {done ? '100%' : '0%'}
                    </Text>
                    <Ionicons name="chevron-forward" color={colors.muted} size={18} />
                  </View>
                </Card>
              </Pressable>
            );
          })}
        </View>
      </KeyboardAwareScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 100, gap: spacing.md },
  progressCard: { gap: spacing.md },
  progressTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  overline: { color: colors.muted, fontSize: 9, fontWeight: '900', letterSpacing: 1.1 },
  progressCount: { color: colors.text, fontSize: 24, fontWeight: '900', marginTop: 4 },
  progressLabel: { color: colors.textSecondary, fontSize: 11, marginTop: 2 },
  bulb: { width: 60, height: 60, borderRadius: 18, backgroundColor: colors.purpleBackground, alignItems: 'center', justifyContent: 'center' },
  track: { height: 7, borderRadius: 999, backgroundColor: colors.border, overflow: 'hidden' },
  fill: { height: '100%', backgroundColor: colors.primary, borderRadius: 999 },
  filters: { gap: spacing.sm, paddingVertical: spacing.sm },
  filterOption: { minHeight: 44, justifyContent: 'center' },
  list: { gap: spacing.md },
  lessonCard: { flexDirection: 'row', gap: spacing.md, alignItems: 'center' },
  lessonIcon: { width: 46, height: 46, borderRadius: 15, alignItems: 'center', justifyContent: 'center' },
  lessonTitle: { color: colors.text, fontSize: 14, fontWeight: '900' },
  lessonMeta: { color: colors.muted, fontSize: 10, marginTop: 4 },
  lessonRight: { alignItems: 'flex-end', gap: 5 },
  completion: { fontSize: 10, fontWeight: '900' }
});
