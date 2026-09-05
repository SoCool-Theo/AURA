import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Text, View } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useAuth } from '../auth/useAuth';
import { useAppData } from '../hooks/useAppData';
import { LoadingState } from '../components/ui/LoadingState';
import { Button } from '../components/ui/Button';
import { colors, spacing } from '../theme/theme';
import { OnboardingScreen } from '../screens/onboarding/OnboardingScreen';
import { SessionRestoreScreen } from '../screens/auth/SessionRestoreScreen';
import { AuthNavigator } from './AuthNavigator';
import { MainTabNavigator } from './MainTabNavigator';
import type { RootStackParamList } from './navigationTypes';

const Stack = createNativeStackNavigator<RootStackParamList>();
const ONBOARDING_KEY = 'aura_onboarding_complete';

export function RootNavigator() {
  const {
    status: authStatus,
    sessionError,
    retrySessionRestore,
    signOut
  } = useAuth();
  const { loading: appDataLoading } = useAppData();
  const [checked, setChecked] = useState(false);
  const [onboarded, setOnboarded] = useState(false);
  const [onboardingError, setOnboardingError] = useState<string | null>(null);
  const onboardingPending = useRef(false);

  const checkOnboarding = useCallback(async () => {
    setChecked(false);
    setOnboardingError(null);
    try { setOnboarded(await AsyncStorage.getItem(ONBOARDING_KEY) === 'true'); }
    catch { setOnboardingError('Could not read device onboarding settings. Please retry.'); }
    finally { setChecked(true); }
  }, []);
  useEffect(() => { void checkOnboarding(); }, [checkOnboarding]);

  if (authStatus === 'initializing' || appDataLoading || !checked) {
    return <LoadingState message="Starting Aura…" />;
  }

  if (authStatus === 'error') {
    return (
      <SessionRestoreScreen
        message={sessionError ?? 'Aura could not verify your saved session.'}
        onRetry={retrySessionRestore}
        onSignOut={signOut}
      />
    );
  }

  if (onboardingError) {
    return <View style={{ flex: 1, justifyContent: 'center', padding: spacing.xl, gap: spacing.lg, backgroundColor: colors.background }}>
      <Text style={{ color: colors.text }}>{onboardingError}</Text>
      <Button title="Retry device settings" onPress={() => void checkOnboarding()} />
    </View>;
  }

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      {!onboarded ? (
        <Stack.Screen name="Onboarding">
          {() => (
            <OnboardingScreen
              onFinish={async () => {
                if (onboardingPending.current) return;
                onboardingPending.current = true;
                try {
                  await AsyncStorage.setItem(ONBOARDING_KEY, 'true');
                  setOnboarded(true);
                } catch { setOnboardingError('Could not save onboarding on this device. Please retry.'); }
                finally { onboardingPending.current = false; }
              }}
            />
          )}
        </Stack.Screen>
      ) : authStatus === 'authenticated' ? (
        <Stack.Screen name="Main" component={MainTabNavigator} />
      ) : (
        <Stack.Screen name="Auth" component={AuthNavigator} />
      )}
    </Stack.Navigator>
  );
}
