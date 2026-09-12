import React, { useEffect, useState } from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useAuth } from '../auth/useAuth';
import { useAppData } from '../hooks/useAppData';
import { SplashScreen } from '../screens/splash/SplashScreen';
import { SessionRestoreScreen } from '../screens/auth/SessionRestoreScreen';
import { WelcomeScreen } from '../screens/welcome/WelcomeScreen';
import { AuthNavigator } from './AuthNavigator';
import { MainTabNavigator } from './MainTabNavigator';
import type {
  AuthStackParamList,
  RootStackParamList
} from './navigationTypes';

const Stack = createNativeStackNavigator<RootStackParamList>();
const MINIMUM_SPLASH_DURATION_MS = 1400;

export function RootNavigator() {
  const {
    status: authStatus,
    sessionExpired,
    sessionError,
    sessionFailure,
    retrySessionRestore,
    signOut
  } = useAuth();
  const { loading: appDataLoading } = useAppData();
  const [minimumSplashElapsed, setMinimumSplashElapsed] = useState(false);
  const [welcomeVisible, setWelcomeVisible] = useState(true);
  const [authEntryRoute, setAuthEntryRoute] = useState<keyof AuthStackParamList>('Login');

  useEffect(() => {
    const timer = setTimeout(
      () => setMinimumSplashElapsed(true),
      MINIMUM_SPLASH_DURATION_MS
    );
    return () => clearTimeout(timer);
  }, []);
  useEffect(() => {
    if (authStatus === 'authenticated') {
      setAuthEntryRoute('Login');
      setWelcomeVisible(false);
    }
  }, [authStatus]);

  if (
    !minimumSplashElapsed
    || authStatus === 'initializing'
    || appDataLoading
  ) {
    return <SplashScreen />;
  }

  if (authStatus === 'error') {
    return (
      <SessionRestoreScreen
        message={sessionError ?? 'Aura could not verify your saved session.'}
        error={sessionFailure}
        onRetry={retrySessionRestore}
        onSignOut={signOut}
      />
    );
  }

  if (authStatus === 'unauthenticated' && welcomeVisible && !sessionExpired) {
    return (
      <WelcomeScreen
        onGetStarted={() => {
          setAuthEntryRoute('Register');
          setWelcomeVisible(false);
        }}
        onLogin={() => {
          setAuthEntryRoute('Login');
          setWelcomeVisible(false);
        }}
      />
    );
  }

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      {authStatus === 'authenticated' ? (
        <Stack.Screen name="Main" component={MainTabNavigator} />
      ) : (
        <Stack.Screen name="Auth">
          {() => <AuthNavigator initialRouteName={authEntryRoute} />}
        </Stack.Screen>
      )}
    </Stack.Navigator>
  );
}
