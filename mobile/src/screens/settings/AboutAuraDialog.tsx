import { Ionicons } from '@expo/vector-icons';
import React from 'react';
import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Button } from '../../components/ui/Button';
import { colors, spacing } from '../../theme/theme';

const features = [
  ['Portfolios & risk', 'Explore current holdings or planned allocations and understand returns, volatility, drawdown, diversification, and risk drivers.'],
  ['What-if simulations', 'Compare hypothetical allocation changes and historical scenarios without changing your original portfolio.'],
  ['AI Assistant', "Ask for plain-language explanations grounded in Aura's portfolio analysis and simulation results."],
  ['Watchlist & Learn', 'Follow supported assets using saved market observations and learn with simple financial examples. Watchlist prices are not live quotes.'],
];

export function AboutAuraDialog({ visible, onClose }: { visible: boolean; onClose: () => void }) {
  return <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
    <View style={styles.overlay}>
      <Pressable style={StyleSheet.absoluteFill} accessibilityRole="button" accessibilityLabel="Close About Aura" onPress={onClose} />
      <View style={styles.dialog} accessibilityViewIsModal>
        <View style={styles.header}>
          <View style={styles.brandIcon}><Ionicons name="shield-checkmark-outline" color={colors.primary} size={24} /></View>
          <View style={{ flex: 1 }}><Text style={styles.eyebrow}>PORTFOLIO RISK EDUCATION</Text><Text accessibilityRole="header" style={styles.title}>About Aura</Text></View>
          <Pressable accessibilityRole="button" accessibilityLabel="Close About Aura" onPress={onClose} style={styles.close}><Ionicons name="close" color={colors.primary} size={20} /></Pressable>
        </View>
        <ScrollView style={{ flexGrow: 0 }} contentContainerStyle={styles.body}>
          <Text style={styles.description}>Aura helps you understand the risks inside a portfolio and make sense of financial results in everyday language.</Text>
          {features.map(([title, description]) => <View key={title} style={styles.feature}><Text accessibilityRole="header" style={styles.featureTitle}>{title}</Text><Text style={styles.description}>{description}</Text></View>)}
          <View style={styles.notice}><Ionicons name="school-outline" color={colors.primary} size={20} /><Text style={[styles.description, { flex: 1, fontSize: 11 }]}>Aura is a portfolio risk education platform, not a trading platform or financial advisor. Historical results do not guarantee future performance; Aura does not provide buy/sell recommendations.</Text></View>
        </ScrollView>
        <View style={styles.footer}><Button title="Done" onPress={onClose} /></View>
      </View>
    </View>
  </Modal>;
}

const styles = StyleSheet.create({
  overlay: { flex: 1, padding: spacing.lg, justifyContent: 'center', backgroundColor: 'rgba(0,4,12,0.78)' },
  dialog: { maxHeight: '90%', flexShrink: 1, overflow: 'hidden', backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.primarySoft, borderRadius: 20 },
  header: { borderTopWidth: 4, borderTopColor: colors.primary, borderBottomWidth: 1, borderBottomColor: colors.border, padding: spacing.lg, flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  brandIcon: { width: 42, height: 42, borderRadius: 12, backgroundColor: colors.selectedBackground, alignItems: 'center', justifyContent: 'center' },
  eyebrow: { color: colors.primary, fontSize: 8, fontWeight: '800', letterSpacing: .5 },
  title: { marginTop: spacing.xs, color: colors.text, fontSize: 20, fontWeight: '900' },
  close: { width: 44, height: 44, borderWidth: 1, borderColor: colors.primarySoft, borderRadius: 12, backgroundColor: colors.selectedBackground, alignItems: 'center', justifyContent: 'center' },
  body: { padding: spacing.lg },
  description: { color: colors.textSecondary, fontSize: 12, lineHeight: 19 },
  feature: { marginTop: spacing.md, padding: spacing.md, borderWidth: 1, borderColor: colors.border, borderRadius: 12, backgroundColor: colors.surfaceAlt },
  featureTitle: { marginBottom: spacing.xs, color: colors.text, fontSize: 13, fontWeight: '800' },
  notice: { marginTop: spacing.lg, padding: spacing.md, borderWidth: 1, borderColor: colors.primarySoft, borderRadius: 12, backgroundColor: colors.selectedBackground, flexDirection: 'row', gap: spacing.sm },
  footer: { padding: spacing.lg, borderTopWidth: 1, borderTopColor: colors.border },
});
