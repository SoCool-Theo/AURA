import { useContext } from 'react';
import { PreferencesContext } from './PreferencesProvider';

export function usePreferences() {
  const value = useContext(PreferencesContext);
  if (!value) {
    throw new Error('usePreferences must be used inside PreferencesProvider');
  }
  return value;
}
