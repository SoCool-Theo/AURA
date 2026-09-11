import AsyncStorage from '@react-native-async-storage/async-storage';

const LEARN_PROGRESS_KEY = 'aura_learn_progress_v1';
// Obsolete domain keys are cleanup targets only. Never read, seed, or save them.
const LEGACY_DOMAIN_KEYS = [
  'aura_local_portfolios_v2',
  'aura_local_reports_v2',
  'aura_local_simulations_v2',
  'aura_active_portfolio_v2',
  'aura_local_watchlist_v1'
];

export async function loadLearnProgress(): Promise<Record<string, boolean>> {
  const raw = await AsyncStorage.getItem(LEARN_PROGRESS_KEY);
  if (!raw) return {};
  const value: unknown = JSON.parse(raw);
  if (!value || typeof value !== 'object' || Array.isArray(value)
    || Object.values(value).some((item) => typeof item !== 'boolean')) {
    throw new Error('Invalid local Learn progress.');
  }
  return value as Record<string, boolean>;
}

export async function saveLearnProgress(progress: Record<string, boolean>) {
  await AsyncStorage.setItem(LEARN_PROGRESS_KEY, JSON.stringify(progress));
}

export async function clearLocalAuraData() {
  await AsyncStorage.multiRemove([...LEGACY_DOMAIN_KEYS, LEARN_PROGRESS_KEY]);
}
