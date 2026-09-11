import AsyncStorage from '@react-native-async-storage/async-storage';
import React, {
  createContext,
  PropsWithChildren,
  useEffect,
  useMemo,
  useState
} from 'react';
import { Appearance } from 'react-native';

export type ThemeMode = 'dark' | 'light';

type PreferencesState = {
  themeMode: ThemeMode;
  notificationsEnabled: boolean;
  hidePortfolioValues: boolean;
  displayName: string;
};

type PreferencesContextValue = PreferencesState & {
  ready: boolean;
  storageError: string | null;
  setThemeMode: (mode: ThemeMode) => void;
  setNotificationsEnabled: (enabled: boolean) => void;
  setHidePortfolioValues: (hidden: boolean) => void;
  setDisplayName: (name: string) => void;
  resetPreferences: () => Promise<void>;
};

const STORAGE_KEY = 'aura_mobile_preferences_v1';

const defaults: PreferencesState = {
  themeMode: 'dark',
  notificationsEnabled: true,
  hidePortfolioValues: false,
  displayName: ''
};

export const PreferencesContext =
  createContext<PreferencesContextValue | undefined>(undefined);

function applyTheme(mode: ThemeMode) {
  const appearance = Appearance as typeof Appearance & {
    setColorScheme?: (scheme: ThemeMode) => void;
  };
  appearance.setColorScheme?.(mode);
}

export function PreferencesProvider({ children }: PropsWithChildren) {
  const [prefs, setPrefs] = useState<PreferencesState>(defaults);
  const [ready, setReady] = useState(false);
  const [storageError, setStorageError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const raw = await AsyncStorage.getItem(STORAGE_KEY);
        if (raw) {
          const saved = JSON.parse(raw) as Partial<PreferencesState>;
          const next = {
            themeMode: saved.themeMode === 'light' ? 'light' as const : 'dark' as const,
            notificationsEnabled: typeof saved.notificationsEnabled === 'boolean' ? saved.notificationsEnabled : defaults.notificationsEnabled,
            hidePortfolioValues: typeof saved.hidePortfolioValues === 'boolean' ? saved.hidePortfolioValues : defaults.hidePortfolioValues,
            displayName: typeof saved.displayName === 'string' ? saved.displayName : ''
          };
          setPrefs(next);
          applyTheme(next.themeMode);
        } else {
          applyTheme(defaults.themeMode);
        }
      } catch {
        applyTheme(defaults.themeMode);
        setStorageError('Device preferences could not be loaded. Defaults are in use; try resetting local data.');
      } finally {
        setReady(true);
      }
    })();
  }, []);

  function update(patch: Partial<PreferencesState>) {
    setPrefs((current) => {
      const next = { ...current, ...patch };
      void AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next))
        .then(() => setStorageError(null))
        .catch(() => setStorageError('This preference changed for now but could not be saved on this device. Try again.'));
      return next;
    });
  }

  const value = useMemo<PreferencesContextValue>(
    () => ({
      ...prefs,
      ready,
      storageError,
      setThemeMode: (mode) => {
        applyTheme(mode);
        update({ themeMode: mode });
      },
      setNotificationsEnabled: (enabled) =>
        update({ notificationsEnabled: enabled }),
      setHidePortfolioValues: (hidden) =>
        update({ hidePortfolioValues: hidden }),
      setDisplayName: (name) => update({ displayName: name.trim() }),
      resetPreferences: async () => {
        await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(defaults));
        applyTheme(defaults.themeMode);
        setPrefs(defaults);
        setStorageError(null);
      }
    }),
    [prefs, ready, storageError]
  );

  return (
    <PreferencesContext.Provider value={value}>
      {children}
    </PreferencesContext.Provider>
  );
}
