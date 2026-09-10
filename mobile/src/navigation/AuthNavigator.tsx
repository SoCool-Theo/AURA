import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { LoginScreen } from '../screens/auth/LoginScreen';
import { RegisterScreen } from '../screens/auth/RegisterScreen';
import type { AuthStackParamList } from './navigationTypes';

const Stack = createNativeStackNavigator<AuthStackParamList>();

export function AuthNavigator({
  initialRouteName = 'Login'
}: {
  initialRouteName?: keyof AuthStackParamList;
}) {
  return (
    <Stack.Navigator
      initialRouteName={initialRouteName}
      screenOptions={{ headerShown: false }}
    >
      <Stack.Screen name="Login" component={LoginScreen} />
      <Stack.Screen name="Register" component={RegisterScreen} />
    </Stack.Navigator>
  );
}
