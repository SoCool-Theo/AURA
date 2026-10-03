import React, { PropsWithChildren } from 'react';
import {
  DarkTheme,
  DefaultTheme,
  NavigationContainer
} from '@react-navigation/native';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { AuthProvider } from '../auth/AuthProvider';
import { PortfolioPrivacyProvider } from '../privacy/PortfolioPrivacy';
import {
  PreferencesProvider
} from '../preferences/PreferencesProvider';
import { usePreferences } from '../preferences/usePreferences';
import { AppDataProvider } from '../storage/AppDataProvider';
import { PortfolioProvider } from '../portfolio/PortfolioProvider';
import { ReportProvider } from '../report/ReportProvider';
import { SimulationProvider } from '../simulation/SimulationProvider';
import { darkPalette, lightPalette } from '../theme/colors';

function NavigationShell({ children }: PropsWithChildren) {
  const { themeMode } = usePreferences();
  const isDark = themeMode === 'dark';
  const palette = isDark ? darkPalette : lightPalette;
  const base = isDark ? DarkTheme : DefaultTheme;

  const navigationTheme = {
    ...base,
    dark: isDark,
    colors: {
      ...base.colors,
      primary: palette.primary,
      background: palette.background,
      card: palette.surface,
      text: palette.text,
      border: palette.border,
      notification: palette.danger
    }
  };

  return (
    <>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <AuthProvider>
        <PortfolioPrivacyProvider>
          <PortfolioProvider>
            <ReportProvider>
              <SimulationProvider>
                <AppDataProvider>
                  <NavigationContainer theme={navigationTheme}>
                    {children}
                  </NavigationContainer>
                </AppDataProvider>
              </SimulationProvider>
            </ReportProvider>
          </PortfolioProvider>
        </PortfolioPrivacyProvider>
      </AuthProvider>
    </>
  );
}

export function AppProviders({ children }: PropsWithChildren) {
  return (
    <SafeAreaProvider>
      <PreferencesProvider>
        <NavigationShell>{children}</NavigationShell>
      </PreferencesProvider>
    </SafeAreaProvider>
  );
}
