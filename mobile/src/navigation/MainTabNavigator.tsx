import React from 'react';
import { Ionicons } from '@expo/vector-icons';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import { DashboardScreen } from '../screens/dashboard/DashboardScreen';
import { PortfoliosScreen } from '../screens/portfolios/PortfoliosScreen';
import { PortfolioDetailScreen } from '../screens/portfolios/PortfolioDetailScreen';
import { CreatePortfolioScreen } from '../screens/portfolios/CreatePortfolioScreen';
import { AddAssetScreen } from '../screens/portfolios/AddAssetScreen';
import { EditHoldingsScreen } from '../screens/portfolios/EditHoldingsScreen';
import { PortfolioAnalysisScreen } from '../screens/analytics/PortfolioAnalysisScreen';
import { ForecastingScreen } from '../screens/forecasting/ForecastingScreen';

import { SimulationsScreen } from '../screens/simulations/SimulationsScreen';
import { HistoricalScenarioScreen } from '../screens/simulations/HistoricalScenarioScreen';
import { AllocationChangeScreen } from '../screens/simulations/AllocationChangeScreen';
import { CombinedSimulationScreen } from '../screens/simulations/CombinedSimulationScreen';
import { SimulationResultScreen } from '../screens/simulations/SimulationResultScreen';
import { SimulationHistoryScreen } from '../screens/simulations/SimulationHistoryScreen';

import { AssistantScreen } from '../screens/assistant/AssistantScreen';
import { MoreScreen } from '../screens/settings/MoreScreen';
import { SettingsScreen } from '../screens/settings/SettingsScreen';
import { HelpSupportScreen } from '../screens/settings/HelpSupportScreen';
import { NotificationsScreen } from '../screens/notifications/NotificationsScreen';
import { ReportsScreen } from '../screens/reports/ReportsScreen';
import { ReportDetailScreen } from '../screens/reports/ReportDetailScreen';
import { AssetRiskDetailScreen } from '../screens/reports/AssetRiskDetailScreen';
import { WatchlistScreen } from '../screens/watchlist/WatchlistScreen';
import { LearnScreen } from '../screens/learn/LearnScreen';
import { LearnDetailScreen } from '../screens/learn/LearnDetailScreen';

import type {
  MainTabParamList,
  PortfolioStackParamList,
  SimulationStackParamList,
  MoreStackParamList
} from './navigationTypes';

import { darkPalette, lightPalette } from '../theme/colors';
import { HomeHeaderButton } from '../components/ui/HomeHeaderButton';
import { BackHeaderButton } from '../components/ui/BackHeaderButton';
import { usePreferences } from '../preferences/usePreferences';
import { tabRootAction } from './tabRootNavigation';

const Tab = createBottomTabNavigator<MainTabParamList>();
const PortfolioStack = createNativeStackNavigator<PortfolioStackParamList>();
const SimulationStack = createNativeStackNavigator<SimulationStackParamList>();
const MoreStack = createNativeStackNavigator<MoreStackParamList>();

function useNavigationPalette() {
  const { themeMode } = usePreferences();
  return themeMode === 'light' ? lightPalette : darkPalette;
}

function PortfolioNavigator() {
  const palette = useNavigationPalette();

  return (
    <PortfolioStack.Navigator
      screenOptions={({ navigation }) => ({
        headerStyle: { backgroundColor: palette.background },
        headerTintColor: palette.text,
        headerTitleStyle: { fontWeight: '900', fontSize: 16 },
        headerShadowVisible: false,
        contentStyle: { backgroundColor: palette.background },
        headerRight: () => <HomeHeaderButton navigation={navigation} />
      })}
    >
      <PortfolioStack.Screen name="Portfolios" component={PortfoliosScreen} options={{ headerShown: false }} />
      <PortfolioStack.Screen
        name="PortfolioDetail"
        component={PortfolioDetailScreen}
        options={({ navigation }) => ({
          title: 'Portfolio',
          headerBackVisible: false,
          headerLeft: () => (
            <BackHeaderButton
              label="Back from Portfolio"
              color={palette.text}
              onPress={() => navigation.canGoBack()
                ? navigation.goBack()
                : navigation.getParent()?.navigate('Home')}
            />
          )
        })}
      />
      <PortfolioStack.Screen name="CreatePortfolio" component={CreatePortfolioScreen} options={{ title: 'Create Portfolio' }} />
      <PortfolioStack.Screen name="AddAsset" component={AddAssetScreen} options={{ title: 'Add Asset' }} />
      <PortfolioStack.Screen name="EditHoldings" component={EditHoldingsScreen} options={{ title: 'Edit Holdings' }} />
      <PortfolioStack.Screen
        name="PortfolioAnalysis"
        component={PortfolioAnalysisScreen}
        options={({ navigation }) => ({
          title: 'Analytics',
          headerBackVisible: false,
          headerLeft: () => (
            <BackHeaderButton
              label="Back from Analytics"
              color={palette.text}
              onPress={() => navigation.canGoBack() ? navigation.goBack() : navigation.navigate('Portfolios')}
            />
          )
        })}
      />
      <PortfolioStack.Screen name="ReportDetail" component={ReportDetailScreen} options={{ title: 'Report Detail' }} />
      <PortfolioStack.Screen name="Forecasting" component={ForecastingScreen} options={({ navigation }) => ({
        title: 'Forecasting', headerBackVisible: false,
        headerLeft: () => <BackHeaderButton label="Back from Forecasting" color={palette.text} onPress={() => navigation.canGoBack() ? navigation.goBack() : navigation.navigate('Portfolios')} />
      })} />
      <PortfolioStack.Screen name="AssetRiskDetail" component={AssetRiskDetailScreen} options={{ title: 'Asset Risk' }} />
    </PortfolioStack.Navigator>
  );
}

function SimulationNavigator() {
  const palette = useNavigationPalette();

  return (
    <SimulationStack.Navigator
      screenOptions={({ navigation }) => ({
        headerStyle: { backgroundColor: palette.background },
        headerTintColor: palette.text,
        headerTitleStyle: { fontWeight: '900', fontSize: 16 },
        headerShadowVisible: false,
        contentStyle: { backgroundColor: palette.background },
        headerRight: () => <HomeHeaderButton navigation={navigation} />
      })}
    >
      <SimulationStack.Screen name="Simulations" component={SimulationsScreen} options={{ headerShown: false }} />
      <SimulationStack.Screen name="HistoricalScenario" component={HistoricalScenarioScreen} options={{ title: 'Historical Scenario' }} />
      <SimulationStack.Screen name="AllocationChange" component={AllocationChangeScreen} options={{ title: 'Allocation Change' }} />
      <SimulationStack.Screen name="CombinedSimulation" component={CombinedSimulationScreen} options={{ title: 'Combined Simulation' }} />
      <SimulationStack.Screen name="SimulationResult" component={SimulationResultScreen} options={{ title: 'Simulation Result' }} />
      <SimulationStack.Screen name="SimulationHistory" component={SimulationHistoryScreen} options={{ title: 'Simulation History' }} />
    </SimulationStack.Navigator>
  );
}

function MoreNavigator() {
  const palette = useNavigationPalette();

  return (
    <MoreStack.Navigator
      screenOptions={({ navigation }) => ({
        headerStyle: { backgroundColor: palette.background },
        headerTintColor: palette.text,
        headerTitleStyle: { fontWeight: '900', fontSize: 16 },
        headerShadowVisible: false,
        contentStyle: { backgroundColor: palette.background },
        headerRight: () => <HomeHeaderButton navigation={navigation} />
      })}
    >
      <MoreStack.Screen name="More" component={MoreScreen} options={{ headerShown: false }} />
      <MoreStack.Screen
        name="Analytics"
        component={PortfolioAnalysisScreen}
        options={({ navigation }) => ({
          title: 'Analytics',
          headerBackVisible: false,
          headerLeft: () => (
            <BackHeaderButton
              label="Back to More"
              color={palette.text}
              onPress={() => navigation.navigate('More')}
            />
          )
        })}
      />
      <MoreStack.Screen
        name="Reports"
        component={ReportsScreen}
        options={({ navigation }) => ({
          title: 'Reports',
          headerBackVisible: false,
          headerLeft: () => (
            <BackHeaderButton
              label="Back to More"
              color={palette.text}
              onPress={() => navigation.popTo('More')}
            />
          )
        })}
      />
      <MoreStack.Screen
        name="ReportDetail"
        component={ReportDetailScreen}
        options={({ navigation }) => ({
          title: 'Report Detail',
          headerBackVisible: false,
          headerLeft: () => (
            <BackHeaderButton
              label="Back to Reports"
              color={palette.text}
              onPress={() => navigation.navigate('Reports')}
            />
          )
        })}
      />
      <MoreStack.Screen name="AssetRiskDetail" component={AssetRiskDetailScreen} options={{ title: 'Asset Risk' }} />
      <MoreStack.Screen name="Watchlist" component={WatchlistScreen} options={{ title: 'Watchlist' }} />
      <MoreStack.Screen name="Forecasting" component={ForecastingScreen} options={({ navigation, route }) => ({
        title: 'Forecasting', headerBackVisible: false,
        headerLeft: () => <BackHeaderButton label={route.params?.returnToHome ? 'Back to Dashboard' : 'Back from Forecasting'} color={palette.text} onPress={() => route.params?.returnToHome ? navigation.getParent()?.navigate('Home') : navigation.canGoBack() ? navigation.goBack() : navigation.navigate('More')} />
      })} />
      <MoreStack.Screen name="Learn" component={LearnScreen} options={{ title: 'Learn' }} />
      <MoreStack.Screen name="LearnDetail" component={LearnDetailScreen} options={{ title: 'Lesson' }} />
      <MoreStack.Screen name="Settings" component={SettingsScreen} options={{ title: 'Settings' }} />
      <MoreStack.Screen name="HelpSupport" component={HelpSupportScreen} options={({ navigation }) => ({
        title: 'Help & Support',
        headerBackVisible: false,
        headerLeft: () => <BackHeaderButton label="Back to Settings" color={palette.text} onPress={() => navigation.popTo('Settings')} />
      })} />
      <MoreStack.Screen name="Notifications" component={NotificationsScreen} options={({ navigation }) => ({
        title: 'Notifications', headerBackVisible: false,
        headerLeft: () => <BackHeaderButton label="Back to More" color={palette.text} onPress={() => navigation.popTo('More')} />
      })} />
      <MoreStack.Screen name="NotificationSettings" component={NotificationsScreen} options={({ navigation }) => ({
        title: 'App notifications', headerBackVisible: false,
        headerLeft: () => <BackHeaderButton label="Back to Settings" color={palette.text} onPress={() => navigation.popTo('Settings')} />
      })} />
    </MoreStack.Navigator>
  );
}

export function MainTabNavigator() {
  const palette = useNavigationPalette();

  return (
    <Tab.Navigator
      screenListeners={({ navigation, route }) => ({
        tabPress: (event) => {
          const action = tabRootAction(route.name);
          if (!action) return;
          event.preventDefault();
          navigation.dispatch(action);
        }
      })}
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarStyle: {
          backgroundColor: palette.tabBar,
          borderTopColor: palette.borderSoft,
          borderTopWidth: 1,
          height: 74,
          paddingBottom: 10,
          paddingTop: 8
        },
        tabBarLabelStyle: {
          fontWeight: '800',
          fontSize: 10
        },
        tabBarActiveTintColor: palette.primary,
        tabBarInactiveTintColor: palette.muted,
        tabBarHideOnKeyboard: true,
        tabBarIcon: ({ color, size }) => {
          const icons: Record<keyof MainTabParamList, keyof typeof Ionicons.glyphMap> = {
            Home: 'home-outline',
            Portfolio: 'pie-chart-outline',
            Simulate: 'pulse-outline',
            AI: 'sparkles-outline',
            MoreTab: 'menu-outline'
          };
          return <Ionicons name={icons[route.name]} color={color} size={size} />;
        }
      })}
    >
      <Tab.Screen name="Home" component={DashboardScreen} />
      <Tab.Screen name="Portfolio" component={PortfolioNavigator} />
      <Tab.Screen name="Simulate" component={SimulationNavigator} />
      <Tab.Screen name="AI" component={AssistantScreen} />
      <Tab.Screen name="MoreTab" component={MoreNavigator} options={{ title: 'More' }} />
    </Tab.Navigator>
  );
}
