import React from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Card } from '../../components/ui/Card';
import { PageTitle } from '../../components/ui/PageTitle';
import { Tag } from '../../components/ui/Tag';
import { useAppData } from '../../hooks/useAppData';
import { colors, spacing } from '../../theme/theme';

export function ReportsScreen({ navigation }: { navigation: any }) {
  const { reports, deleteReport } = useAppData();

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content}>
        <PageTitle title="Reports" subtitle="Saved analysis snapshots and simulation records." />

        <View style={styles.search}>
          <Ionicons name="search-outline" color={colors.muted} size={17} />
          <Text style={styles.searchText}>Search reports</Text>
        </View>

        <View style={styles.filterRow}>
          <Tag label="All" tone="primary" />
          <Tag label="Analysis" />
          <Tag label="Simulation" />
        </View>

        <View style={styles.list}>
          {reports.length ? reports.map((report, index) => (
            <Pressable
              key={report.id}
              onPress={() => navigation.navigate('ReportDetail', { reportId: report.id })}
            >
              <Card style={styles.reportCard}>
                <View style={[styles.icon, { backgroundColor: index % 2 === 0 ? colors.purpleBackground : colors.cyanBackground }]}>
                  <Ionicons
                    name="document-text-outline"
                    color={index % 2 === 0 ? colors.purpleSoft : colors.primary}
                    size={22}
                  />
                </View>

                <View style={{ flex: 1 }}>
                  <Text style={styles.title}>{report.portfolioName} Analysis</Text>
                  <Text style={styles.date}>{new Date(report.createdAt).toLocaleString()}</Text>
                  <Text style={styles.type}>Analysis Report</Text>
                </View>

                <Pressable
                  onPress={() => Alert.alert('Delete report?', 'Remove this local report?', [
                    { text: 'Cancel', style: 'cancel' },
                    { text: 'Delete', style: 'destructive', onPress: () => deleteReport(report.id) }
                  ])}
                  style={styles.delete}
                >
                  <Ionicons name="trash-outline" color={colors.muted} size={17} />
                </Pressable>
              </Card>
            </Pressable>
          )) : (
            <Card style={styles.empty}>
              <Ionicons name="document-text-outline" color={colors.muted} size={30} />
              <Text style={styles.emptyTitle}>No reports saved</Text>
              <Text style={styles.emptyText}>Open Analytics and save a report snapshot.</Text>
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
  searchText: { color: colors.muted, fontSize: 12 },
  filterRow: { flexDirection: 'row', gap: spacing.sm, marginVertical: spacing.lg },
  list: { gap: spacing.md },
  reportCard: { flexDirection: 'row', gap: spacing.md, alignItems: 'center' },
  icon: { width: 48, height: 48, borderRadius: 15, alignItems: 'center', justifyContent: 'center' },
  title: { color: colors.text, fontWeight: '900', fontSize: 14 },
  date: { color: colors.muted, fontSize: 10, marginTop: 4 },
  type: { color: colors.primary, fontSize: 10, fontWeight: '800', marginTop: 4 },
  delete: { width: 36, height: 36, borderRadius: 12, backgroundColor: colors.surfaceAlt, alignItems: 'center', justifyContent: 'center' },
  empty: { alignItems: 'center', gap: spacing.sm, paddingVertical: spacing.xxl },
  emptyTitle: { color: colors.text, fontWeight: '900' },
  emptyText: { color: colors.muted, fontSize: 12, textAlign: 'center' }
});
