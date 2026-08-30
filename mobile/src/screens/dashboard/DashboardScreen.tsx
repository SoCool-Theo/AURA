import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import { Card } from '../../components/ui/Card';
import { Tag } from '../../components/ui/Tag';
import { RiskGauge } from '../../components/charts/RiskGauge';

import { useAuth } from '../../auth/useAuth';
import { useAppData } from '../../hooks/useAppData';
import { usePreferences } from '../../preferences/usePreferences';
import { demoAnalyzePortfolio } from '../../utils/localCalculations';

import { colors, spacing } from '../../theme/theme';
import { formatCurrency, formatPercent } from '../../utils/formatting';

const actions = [
  {
    label: 'Analyze',
    subtitle: 'See your risk breakdown',
    icon: 'analytics-outline' as const,
    color: colors.primary,
    background: colors.cyanBackground
  },
  {
    label: 'Simulate',
    subtitle: 'Run a What-If scenario',
    icon: 'pulse-outline' as const,
    color: colors.purpleSoft,
    background: colors.purpleBackground
  },
  {
    label: 'Ask Aura',
    subtitle: 'Explain results simply',
    icon: 'sparkles-outline' as const,
    color: colors.blue,
    background: colors.blueBackground
  },
  {
    label: 'Add Asset',
    subtitle: 'Update your holdings',
    icon: 'add-circle-outline' as const,
    color: colors.warning,
    background: colors.warningBackground
  }
];

export function DashboardScreen({ navigation }: { navigation: any }) {
  const { user } = useAuth();
  const { activePortfolio } = useAppData();
  const { displayName, hidePortfolioValues } = usePreferences();

  if (!activePortfolio) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.empty}>
          <Text style={styles.brand}>AURA</Text>
          <Text style={styles.greeting}>Welcome, {displayName || user?.name || 'Investor'}</Text>
          <Text style={styles.emptyText}>Create a portfolio to start understanding your risk.</Text>
          <Pressable
            style={styles.createButton}
            onPress={() =>
              navigation.navigate('Portfolio', { screen: 'CreatePortfolio' })
            }
          >
            <Text style={styles.createButtonText}>Create Portfolio</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  const portfolio = activePortfolio;
  const analysis = demoAnalyzePortfolio(portfolio);
  const firstName = (displayName || user?.name || 'Investor').split(' ')[0];
  const primaryDriver = analysis.topRiskDrivers[0];

  function handleAction(label: string) {
    if (label === 'Analyze') {
      navigation.navigate('Portfolio', {
        screen: 'PortfolioAnalysis',
        params: { portfolioId: portfolio.id }
      });
      return;
    }

    if (label === 'Simulate') {
      navigation.navigate('Simulate');
      return;
    }

    if (label === 'Ask Aura') {
      navigation.navigate('AI');
      return;
    }

    navigation.navigate('Portfolio', {
      screen: 'AddAsset',
      params: { portfolioId: portfolio.id }
    });
  }

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.header}>
          <View>
            <Text style={styles.brand}>AURA</Text>
            <Text style={styles.greeting}>Good evening, {firstName}</Text>
            <Text style={styles.subtitle}>Here’s how your portfolio looks today.</Text>
          </View>

          <Pressable
            style={styles.profileButton}
            onPress={() => navigation.navigate('MoreTab')}
          >
            <Ionicons name="person-outline" color={colors.text} size={20} />
          </Pressable>
        </View>

        <Card style={styles.portfolioCard}>
          <View style={styles.portfolioTop}>
            <View style={styles.portfolioCopy}>
              <View style={styles.activeRow}>
                <View style={styles.activeDot} />
                <Text style={styles.activeText}>ACTIVE PORTFOLIO</Text>
              </View>

              <Text style={styles.portfolioName}>{portfolio.name}</Text>
              <Text style={styles.totalValue}>{hidePortfolioValues ? '••••••' : formatCurrency(portfolio.totalValue)}</Text>
              <Text style={styles.totalLabel}>Total portfolio value</Text>

              <Pressable
                style={styles.portfolioLink}
                onPress={() =>
                  navigation.navigate('Portfolio', {
                    screen: 'PortfolioDetail',
                    params: { portfolioId: portfolio.id }
                  })
                }
              >
                <Text style={styles.portfolioLinkText}>View portfolio</Text>
                <Ionicons name="arrow-forward" color={colors.primary} size={15} />
              </Pressable>
            </View>

            <View style={styles.riskSide}>
              <RiskGauge score={analysis.riskScore} size={112} strokeWidth={9} />
              <Tag
                label={analysis.riskLevel}
                tone={
                  analysis.riskScore >= 70
                    ? 'danger'
                    : analysis.riskScore >= 40
                      ? 'warning'
                      : 'success'
                }
              />
            </View>
          </View>
        </Card>

        <View style={styles.metricRow}>
          <Card style={styles.metricCard}>
            <View style={styles.metricIcon}>
              <Ionicons name="trending-up-outline" color={colors.success} size={18} />
            </View>
            <Text style={styles.metricLabel}>Annual return</Text>
            <Text style={[styles.metricValue, { color: colors.success }]}>
              {formatPercent(analysis.annualizedReturn)}
            </Text>
          </Card>

          <Card style={styles.metricCard}>
            <View style={[styles.metricIcon, { backgroundColor: colors.warningBackground }]}>
              <Ionicons name="pulse-outline" color={colors.warning} size={18} />
            </View>
            <Text style={styles.metricLabel}>Volatility</Text>
            <Text style={styles.metricValue}>{formatPercent(analysis.volatility)}</Text>
          </Card>
        </View>

        <Text style={styles.sectionTitle}>Main risk driver</Text>

        <Card style={styles.driverCard}>
          <View style={styles.driverIcon}>
            <Ionicons name="warning-outline" color={colors.warning} size={22} />
          </View>

          <View style={{ flex: 1 }}>
            <View style={styles.driverTop}>
              <Text style={styles.driverTitle}>
                {primaryDriver?.symbol ?? 'Portfolio concentration'}
              </Text>
              <Tag label={primaryDriver?.level ?? 'Moderate'} tone="warning" />
            </View>
            <Text style={styles.driverText}>
              {primaryDriver?.explanation ??
                'Aura will highlight the largest contributor to your portfolio risk here.'}
            </Text>
          </View>
        </Card>

        <Text style={styles.sectionTitle}>What would you like to do?</Text>

        <View style={styles.actionGrid}>
          {actions.map((action) => (
            <Pressable
              key={action.label}
              style={styles.actionCard}
              onPress={() => handleAction(action.label)}
            >
              <View style={[styles.actionIcon, { backgroundColor: action.background }]}>
                <Ionicons name={action.icon} color={action.color} size={22} />
              </View>

              <Text style={styles.actionTitle}>{action.label}</Text>
              <Text style={styles.actionSubtitle}>{action.subtitle}</Text>

              <Ionicons
                name="arrow-forward"
                color={action.color}
                size={16}
                style={styles.actionArrow}
              />
            </Pressable>
          ))}
        </View>

        <Pressable
          style={styles.learnStrip}
          onPress={() => navigation.navigate('MoreTab', { screen: 'Learn' })}
        >
          <View style={styles.learnIcon}>
            <Ionicons name="school-outline" color={colors.purpleSoft} size={19} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.learnTitle}>Learn about portfolio risk</Text>
            <Text style={styles.learnText}>Short lessons designed for beginner investors.</Text>
          </View>
          <Ionicons name="chevron-forward" color={colors.muted} size={18} />
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.background
  },
  content: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: 108
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: spacing.md,
    marginBottom: spacing.xl
  },
  brand: {
    color: colors.primary,
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 1.8
  },
  greeting: {
    color: colors.text,
    fontSize: 27,
    lineHeight: 32,
    fontWeight: '900',
    marginTop: 6
  },
  subtitle: {
    color: colors.textSecondary,
    fontSize: 12,
    marginTop: 5
  },
  profileButton: {
    width: 40,
    height: 40,
    borderRadius: 14,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center'
  },
  portfolioCard: {
    padding: spacing.lg
  },
  portfolioTop: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md
  },
  portfolioCopy: {
    flex: 1
  },
  activeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6
  },
  activeDot: {
    width: 7,
    height: 7,
    borderRadius: 99,
    backgroundColor: colors.success
  },
  activeText: {
    color: colors.muted,
    fontSize: 9,
    fontWeight: '900',
    letterSpacing: 1
  },
  portfolioName: {
    color: colors.text,
    fontSize: 17,
    fontWeight: '900',
    marginTop: 8
  },
  totalValue: {
    color: colors.text,
    fontSize: 29,
    fontWeight: '900',
    marginTop: 7
  },
  totalLabel: {
    color: colors.muted,
    fontSize: 10,
    marginTop: 3
  },
  portfolioLink: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: spacing.md
  },
  portfolioLinkText: {
    color: colors.primary,
    fontSize: 11,
    fontWeight: '900'
  },
  riskSide: {
    width: 120,
    alignItems: 'center',
    gap: spacing.sm
  },
  metricRow: {
    flexDirection: 'row',
    gap: spacing.md,
    marginTop: spacing.md
  },
  metricCard: {
    flex: 1,
    minHeight: 116
  },
  metricIcon: {
    width: 34,
    height: 34,
    borderRadius: 11,
    backgroundColor: colors.positiveBackground,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.md
  },
  metricLabel: {
    color: colors.muted,
    fontSize: 10,
    fontWeight: '800'
  },
  metricValue: {
    color: colors.text,
    fontSize: 20,
    fontWeight: '900',
    marginTop: 4
  },
  sectionTitle: {
    color: colors.text,
    fontSize: 18,
    fontWeight: '900',
    marginTop: spacing.xl,
    marginBottom: spacing.md
  },
  driverCard: {
    flexDirection: 'row',
    gap: spacing.md,
    alignItems: 'flex-start'
  },
  driverIcon: {
    width: 44,
    height: 44,
    borderRadius: 14,
    backgroundColor: colors.warningBackground,
    alignItems: 'center',
    justifyContent: 'center'
  },
  driverTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: spacing.sm
  },
  driverTitle: {
    color: colors.text,
    fontSize: 15,
    fontWeight: '900',
    flex: 1
  },
  driverText: {
    color: colors.textSecondary,
    fontSize: 12,
    lineHeight: 18,
    marginTop: 7
  },
  actionGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md
  },
  actionCard: {
    width: '47.8%',
    minHeight: 146,
    backgroundColor: colors.surface,
    borderRadius: 17,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    padding: spacing.md
  },
  actionIcon: {
    width: 42,
    height: 42,
    borderRadius: 13,
    alignItems: 'center',
    justifyContent: 'center'
  },
  actionTitle: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '900',
    marginTop: spacing.md
  },
  actionSubtitle: {
    color: colors.muted,
    fontSize: 10,
    lineHeight: 15,
    marginTop: 4,
    paddingRight: 12
  },
  actionArrow: {
    position: 'absolute',
    right: 13,
    bottom: 13
  },
  learnStrip: {
    minHeight: 68,
    backgroundColor: colors.surface,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    padding: spacing.md,
    marginTop: spacing.xl
  },
  learnIcon: {
    width: 40,
    height: 40,
    borderRadius: 13,
    backgroundColor: colors.purpleBackground,
    alignItems: 'center',
    justifyContent: 'center'
  },
  learnTitle: {
    color: colors.text,
    fontSize: 12,
    fontWeight: '900'
  },
  learnText: {
    color: colors.muted,
    fontSize: 10,
    marginTop: 3
  },
  empty: {
    flex: 1,
    justifyContent: 'center',
    padding: spacing.xl
  },
  emptyText: {
    color: colors.textSecondary,
    marginTop: spacing.sm,
    lineHeight: 20
  },
  createButton: {
    minHeight: 50,
    backgroundColor: colors.primary,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: spacing.xl
  },
  createButtonText: {
    color: colors.onPrimary,
    fontWeight: '900'
  }
});
