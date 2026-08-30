import React, { useEffect, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useAuth } from '../auth/useAuth';
import { useAppData } from '../hooks/useAppData';
import { LoadingState } from '../components/ui/LoadingState';
import { OnboardingScreen } from '../screens/onboarding/OnboardingScreen';
import { AuthNavigator } from './AuthNavigator';
import { MainTabNavigator } from './MainTabNavigator';
import type { RootStackParamList } from './navigationTypes';

const Stack = createNativeStackNavigator<RootStackParamList>();
const ONBOARDING_KEY = 'aura_onboarding_complete';

export function RootNavigator() {
  const { user, isLoading: authLoading } = useAuth();
  const { loading: appDataLoading } = useAppData();
  const [checked, setChecked] = useState(false);
  const [onboarded, setOnboarded] = useState(false);

  useEffect(() => {
    AsyncStorage.getItem(ONBOARDING_KEY).then((value) => {
      setOnboarded(value === 'true');
      setChecked(true);
    });
  }, []);

  if (authLoading || appDataLoading || !checked) {
    return <LoadingState message="Starting Aura…" />;
  }

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      {!onboarded ? (
        <Stack.Screen name="Onboarding">
          {() => (
            <OnboardingScreen
              onFinish={async () => {
                await AsyncStorage.setItem(ONBOARDING_KEY, 'true');
                setOnboarded(true);
              }}
            />
          )}
        </Stack.Screen>
      ) : user ? (
        <Stack.Screen name="Main" component={MainTabNavigator} />
      ) : (
        <Stack.Screen name="Auth" component={AuthNavigator} />
      )}
    </Stack.Navigator>
  );
}
