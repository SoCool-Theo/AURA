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
  setThemeMode: (mode: ThemeMode) => void;
  setNotificationsEnabled: (enabled: boolean) => void;
  setHidePortfolioValues: (hidden: boolean) => void;
  setDisplayName: (name: string) => void;
  resetPreferences: () => void;
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

  useEffect(() => {
    (async () => {
      const raw = await AsyncStorage.getItem(STORAGE_KEY);
      if (raw) {
        try {
          const saved = JSON.parse(raw) as Partial<PreferencesState>;
          const next = { ...defaults, ...saved };
          setPrefs(next);
          applyTheme(next.themeMode);
        } catch {
          applyTheme(defaults.themeMode);
        }
      } else {
        applyTheme(defaults.themeMode);
      }
      setReady(true);
    })();
  }, []);

  function update(patch: Partial<PreferencesState>) {
    setPrefs((current) => {
      const next = { ...current, ...patch };
      void AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  }

  const value = useMemo<PreferencesContextValue>(
    () => ({
      ...prefs,
      ready,
      setThemeMode: (mode) => {
        applyTheme(mode);
        update({ themeMode: mode });
      },
      setNotificationsEnabled: (enabled) =>
        update({ notificationsEnabled: enabled }),
      setHidePortfolioValues: (hidden) =>
        update({ hidePortfolioValues: hidden }),
      setDisplayName: (name) => update({ displayName: name.trim() }),
      resetPreferences: () => {
        applyTheme(defaults.themeMode);
        setPrefs(defaults);
        void AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(defaults));
      }
    }),
    [prefs, ready]
  );

  return (
    <PreferencesContext.Provider value={value}>
      {children}
    </PreferencesContext.Provider>
  );
}
