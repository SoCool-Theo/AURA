import React from 'react';
import { AppProviders } from './AppProviders';
import { RootNavigator } from '../navigation/RootNavigator';

export default function App() {
  return (
    <AppProviders>
      <RootNavigator />
    </AppProviders>
  );
}
