import React, { useMemo, useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import { Card } from '../../components/ui/Card';
import { PageTitle } from '../../components/ui/PageTitle';
import { Tag } from '../../components/ui/Tag';
import { useAppData } from '../../hooks/useAppData';
import { colors, spacing } from '../../theme/theme';

const filters = ['All', 'Low Risk', 'Moderate Risk', 'High Risk'] as const;
type Filter = (typeof filters)[number];

export function ReportsScreen({ navigation }: { navigation: any }) {
  const { reports, deleteReport } = useAppData();
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<Filter>('All');

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return reports.filter((report) => {
      const matchesQuery = !q || report.portfolioName.toLowerCase().includes(q);
      const risk = report.analysis.riskLevel.toLowerCase();
      const matchesFilter = filter === 'All' || risk.includes(filter.replace(' Risk', '').toLowerCase());
      return matchesQuery && matchesFilter;
    });
  }, [reports, query, filter]);

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <PageTitle title="Reports" subtitle="Saved immutable portfolio-analysis snapshots." />

        <View style={styles.search}>
          <Ionicons name="search-outline" color={colors.muted} size={17} />
          <TextInput value={query} onChangeText={setQuery} placeholder="Search reports" placeholderTextColor={colors.muted} style={styles.searchInput} />
        </View>

        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filterRow}>
          {filters.map((item) => (
            <Pressable key={item} onPress={() => setFilter(item)}>
              <Tag label={item} tone={filter === item ? 'primary' : 'default'} />
            </Pressable>
          ))}
        </ScrollView>

        <View style={styles.tableHeader}>
          <Text style={[styles.headerText, { flex: 1.7 }]}>Report</Text>
          <Text style={styles.headerText}>Risk</Text>
          <Text style={styles.headerText}>Date</Text>
        </View>

        <View style={styles.list}>
          {filtered.length ? filtered.map((report) => (
            <Pressable key={report.id} onPress={() => navigation.navigate('ReportDetail', { reportId: report.id })}>
              <Card style={styles.reportCard}>
                <View style={styles.icon}><Ionicons name="document-text-outline" color={colors.primary} size={22} /></View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.title}>{report.portfolioName} Analysis</Text>
                  <Text style={styles.type}>Analysis Report</Text>
                  <View style={styles.metaRow}>
                    <Tag label={report.analysis.riskLevel} tone={report.analysis.riskLevel.toLowerCase().includes('high') ? 'danger' : report.analysis.riskLevel.toLowerCase().includes('low') ? 'success' : 'warning'} />
                    <Text style={styles.date}>{new Date(report.createdAt).toLocaleDateString()}</Text>
                  </View>
                </View>
                <Pressable onPress={() => Alert.alert('Delete report?', 'Remove this local snapshot?', [
                  { text: 'Cancel', style: 'cancel' },
                  { text: 'Delete', style: 'destructive', onPress: () => deleteReport(report.id) }
                ])} style={styles.delete}>
                  <Ionicons name="trash-outline" color={colors.muted} size={17} />
                </Pressable>
              </Card>
            </Pressable>
          )) : (
            <Card style={styles.empty}>
              <Ionicons name="document-text-outline" color={colors.muted} size={30} />
              <Text style={styles.emptyTitle}>No matching reports</Text>
              <Text style={styles.emptyText}>Run Analytics and save a report snapshot, or change the current filter.</Text>
            </Card>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 100 },
  search: { height: 44, borderRadius: 13, backgroundColor: colors.surfaceAlt, borderWidth: 1, borderColor: colors.borderSoft, flexDirection: 'row', alignItems: 'center', gap: spacing.sm, paddingHorizontal: spacing.md, marginTop: spacing.xl },
  searchInput: { flex: 1, color: colors.text, fontSize: 12 },
  filterRow: { gap: spacing.sm, paddingVertical: spacing.lg },
  tableHeader: { flexDirection: 'row', gap: spacing.sm, paddingHorizontal: spacing.sm, marginBottom: spacing.sm },
  headerText: { color: colors.muted, fontSize: 8, fontWeight: '900', textTransform: 'uppercase', letterSpacing: 0.7 },
  list: { gap: spacing.md },
  reportCard: { flexDirection: 'row', gap: spacing.md, alignItems: 'center' },
  icon: { width: 48, height: 48, borderRadius: 15, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.cyanBackground },
  title: { color: colors.text, fontWeight: '900', fontSize: 14 },
  type: { color: colors.textSecondary, fontSize: 10, marginTop: 4 },
  metaRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, marginTop: spacing.sm },
  date: { color: colors.muted, fontSize: 9 },
  delete: { width: 36, height: 36, borderRadius: 12, backgroundColor: colors.surfaceAlt, alignItems: 'center', justifyContent: 'center' },
  empty: { alignItems: 'center', gap: spacing.sm, paddingVertical: spacing.xxl },
  emptyTitle: { color: colors.text, fontWeight: '900' },
  emptyText: { color: colors.muted, fontSize: 12, textAlign: 'center', lineHeight: 18 }
});
