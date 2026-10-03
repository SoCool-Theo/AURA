import React from 'react';
import { Pressable, RefreshControl, ScrollView, StyleSheet, Switch, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { BottomTabNavigationProp } from '@react-navigation/bottom-tabs';
import type { MainTabParamList, MoreStackParamList } from '../../navigation/navigationTypes';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { PageTitle } from '../../components/ui/PageTitle';
import { notificationPreferenceRows, useNotificationCenter } from '../../notifications/useNotifications';
import { watchNotificationForeground } from '../../notifications/notificationForeground';
import { colors, spacing } from '../../theme/theme';

export function NotificationsScreen({ route, navigation }: NativeStackScreenProps<MoreStackParamList, 'Notifications' | 'NotificationSettings'>) {
  const settings = route.name === 'NotificationSettings';
  const center = useNotificationCenter(settings);
  const disabled = center.loading || center.busy;
  useFocusEffect(React.useCallback(() => {
    void center.refresh();
    if (!settings) return watchNotificationForeground(() => void center.refresh());
  }, [settings, center.refresh]));
  return <SafeAreaView edges={['bottom']} style={styles.safe}>
    <ScrollView contentContainerStyle={styles.content} refreshControl={<RefreshControl refreshing={center.loading} onRefresh={() => { if (!center.busy) void center.refresh(); }} tintColor={colors.primary} />}>
      <PageTitle eyebrow="AURA UPDATES" title={settings ? 'App notifications' : 'Notifications'} subtitle={settings ? 'Choose which updates you receive inside Aura.' : 'Your saved analysis and simulation updates, newest first.'} />
      <Button variant="secondary" title={settings ? 'Open inbox' : 'Notification settings'} onPress={() => navigation.navigate(settings ? 'Notifications' : 'NotificationSettings')} />
      {center.error && <Card><Text accessibilityRole="alert" style={styles.error}>{center.error}</Text><Button variant="secondary" title="Retry / refresh" disabled={disabled} onPress={() => void center.refresh()} /></Card>}
      {center.notice && <Text accessibilityLiveRegion="polite" style={styles.notice}>{center.notice}</Text>}
      {center.loading && <Text style={styles.helper}>Loading notifications…</Text>}
      {settings && center.prefs && <Card>
        {notificationPreferenceRows.map(row => <View style={styles.preference} key={row.key}>
          <View style={styles.copy}><Text style={styles.title}>{row.title}</Text><Text style={styles.helper}>{row.description}</Text></View>
          <Switch accessibilityLabel={row.title} value={center.prefs![row.key]} disabled={disabled || (row.key !== 'enabled' && !center.prefs!.enabled)} onValueChange={value => void center.toggle(row.key, value)} trackColor={{ false: colors.border, true: colors.primary }} thumbColor={colors.text} />
        </View>)}
        <Text style={styles.helper}>Remembered for your account on web and mobile, including after signing out. Turning this off stops future notifications; existing messages stay in your inbox. Reset local data does not change these account preferences.</Text>
        <Text style={styles.helper}>Phone push, browser push, email notifications, and price alerts are not enabled.</Text>
      </Card>}
      {!settings && center.feed && <>
        <Text accessibilityLiveRegion="polite" style={styles.helper}>{center.feed.unread_count} unread · {center.feed.total} total</Text>
        <Button title="Mark all as read" variant="secondary" disabled={disabled || !center.feed.unread_count} onPress={() => void center.markAll()} />
        {center.feed.items.length === 0 ? <Card style={styles.empty}>
          <Ionicons name="notifications-outline" size={32} color={colors.primary} /><Text style={styles.title}>You’re all caught up</Text>
          <Text style={styles.helper}>New analysis reports and saved simulations will appear here when notifications are enabled. Older results are not added automatically.</Text>
        </Card> : center.feed.items.map(item => <Card key={item.id} style={!item.read_at ? styles.unread : undefined}>
          <View style={styles.heading}><Ionicons name={item.kind === 'analysis' ? 'document-text-outline' : 'pulse-outline'} size={22} color={colors.primary} />
            <Text style={styles.title}>{item.title}</Text>{!item.read_at && <Text style={styles.notice}>Unread</Text>}</View>
          <Text style={styles.body}>{item.message}</Text><Text style={styles.helper}>{new Date(item.created_at).toLocaleString()}</Text>
          <Button title={item.kind === 'analysis' ? 'View report →' : 'View simulation →'} variant="secondary" disabled={disabled} onPress={() => void center.open(item, () => {
            if (item.kind === 'analysis') navigation.navigate('ReportDetail', { portfolioId: item.portfolio_id, reportId: item.resource_id });
            else navigation.getParent<BottomTabNavigationProp<MainTabParamList>>()?.navigate('Simulate', { screen: 'SimulationResult', params: { portfolioId: item.portfolio_id, simulationId: item.resource_id } });
          })} />
          {!item.read_at && <Pressable accessibilityRole="button" accessibilityLabel="Mark as read" disabled={disabled} onPress={() => void center.markRead(item)} style={styles.read}><Text style={styles.notice}>Mark as read</Text></Pressable>}
        </Card>)}
        <View style={styles.pagination}>
          <Button title="Previous" variant="secondary" disabled={disabled || center.offset === 0} onPress={center.previous} />
          <Text style={styles.helper}>{Math.floor(center.offset / 25) + 1}</Text>
          <Button title="Next" variant="secondary" disabled={disabled || center.offset + center.feed.items.length >= center.feed.total || center.offset >= 10000} onPress={center.next} />
        </View>
      </>}
    </ScrollView>
  </SafeAreaView>;
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: 108, gap: spacing.lg },
  helper: { color: colors.muted, fontSize: 12, lineHeight: 20, marginVertical: 6 },
  title: { color: colors.text, fontSize: 15, lineHeight: 22, fontWeight: '800', flexShrink: 1 },
  body: { color: colors.textSecondary, fontSize: 14, lineHeight: 23, marginTop: 10 },
  notice: { color: colors.primary, fontSize: 12, fontWeight: '700' },
  error: { color: colors.danger, lineHeight: 22, marginBottom: 14 },
  preference: { flexDirection: 'row', gap: spacing.md, alignItems: 'center', borderBottomWidth: 1, borderBottomColor: colors.borderSoft, paddingVertical: 18 },
  copy: { flex: 1 },
  heading: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: spacing.sm },
  unread: { borderColor: colors.primary },
  empty: { alignItems: 'center', gap: spacing.sm },
  read: { paddingVertical: 14, alignItems: 'center', minHeight: 44 },
  pagination: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: spacing.sm },
});
