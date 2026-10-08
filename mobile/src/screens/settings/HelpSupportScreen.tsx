import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { KeyboardAwareScrollView } from '../../components/ui/KeyboardAwareScrollView';
import { PageTitle } from '../../components/ui/PageTitle';
import { colors, spacing } from '../../theme/theme';
import { filterHelpSections } from './helpContent';

export function HelpSupportScreen() {
  const [query, setQuery] = useState('');
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const sections = filterHelpSections(query);
  const count = sections.reduce((total, section) => total + section.articles.length, 0);

  return <SafeAreaView style={styles.safe} edges={['bottom']}>
    <KeyboardAwareScrollView contentContainerStyle={styles.content}>
      <PageTitle eyebrow="AURA SUPPORT CENTER" title="Help & Support"
        subtitle="Find clear answers about portfolios, results, privacy, and using Aura." />
      <Input accessibilityLabel="Search help articles" value={query} onChangeText={setQuery}
        placeholder="Search questions or features…" autoCorrect={false} returnKeyType="search" />
      <Text accessibilityLiveRegion="polite" style={styles.results}>{count} {count === 1 ? 'article' : 'articles'}{query.trim() ? ' found' : ' available'} · Tap a question to read the answer.</Text>
      {sections.map(section => <Card key={section.id} style={styles.section}>
        <Text accessibilityRole="header" style={styles.sectionTitle}>{section.title}</Text>
        {section.articles.map(article => <View key={article.id} style={styles.article}>
          <Pressable accessibilityRole="button" accessibilityLabel={article.question}
            accessibilityState={{ expanded: Boolean(expanded[article.id]) }}
            onPress={() => setExpanded(current => ({ ...current, [article.id]: !current[article.id] }))}
            style={styles.question}>
            <Text style={styles.questionText}>{article.question}</Text>
            <Ionicons name={expanded[article.id] ? 'chevron-up' : 'chevron-down'} size={18} color={colors.primary} />
          </Pressable>
          {expanded[article.id] && <View style={styles.answer}>
            {article.answer.map((paragraph, index) => <Text key={index} style={styles.paragraph}>{paragraph}</Text>)}
          </View>}
        </View>)}
      </Card>)}
      {count === 0 && <Card style={styles.empty}>
        <Ionicons name="search-outline" size={26} color={colors.primary} />
        <Text style={styles.sectionTitle}>No matching help articles</Text>
        <Text style={styles.paragraph}>Try a topic such as “portfolio”, “privacy”, or “simulation”.</Text>
        <Button title="Clear search" variant="secondary" onPress={() => setQuery('')} />
      </Card>}
      <View style={styles.boundary}>
        <Ionicons name="shield-checkmark-outline" size={18} color={colors.primary} />
        <Text style={styles.boundaryText}>Aura is a portfolio risk education platform. Its guidance and historical results are not financial or investment advice.</Text>
      </View>
    </KeyboardAwareScrollView>
  </SafeAreaView>;
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 108, gap: spacing.lg },
  results: { color: colors.muted, fontSize: 12, lineHeight: 19 },
  section: { gap: spacing.sm },
  sectionTitle: { color: colors.primary, fontSize: 18, fontWeight: '900' },
  article: { borderTopWidth: 1, borderTopColor: colors.borderSoft },
  question: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, paddingVertical: 16, minHeight: 48 },
  questionText: { flex: 1, color: colors.text, fontSize: 14, fontWeight: '800', lineHeight: 22 },
  answer: { gap: spacing.md, paddingBottom: spacing.lg },
  paragraph: { color: colors.textSecondary, fontSize: 14, lineHeight: 23 },
  empty: { alignItems: 'center', gap: spacing.md },
  boundary: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.sm },
  boundaryText: { flex: 1, color: colors.muted, fontSize: 12, lineHeight: 19 },
});
