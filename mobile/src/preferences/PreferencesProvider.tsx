import AsyncStorage from '@react-native-async-storage/async-storage';
import React, {
  createContext,
  PropsWithChildren,
  useEffect,
  useMemo,
  useRef,
  useState
} from 'react';
import { Appearance } from 'react-native';

export type ThemeMode = 'dark' | 'light';

type PreferencesState = {
  themeMode: ThemeMode;
  notificationsEnabled: boolean;
};

type PreferencesContextValue = PreferencesState & {
  ready: boolean;
  storageError: string | null;
  setThemeMode: (mode: ThemeMode) => void;
  setNotificationsEnabled: (enabled: boolean) => void;
  resetPreferences: () => Promise<void>;
};

const STORAGE_KEY = 'aura_mobile_preferences_v1';

const defaults: PreferencesState = {
  themeMode: 'dark',
  notificationsEnabled: true
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
  const currentPrefs = useRef(defaults);
  const writes = useRef(Promise.resolve());

  useEffect(() => {
    (async () => {
      try {
        const raw = await AsyncStorage.getItem(STORAGE_KEY);
        if (raw) {
          const saved = JSON.parse(raw) as Partial<PreferencesState>;
          const next = {
            themeMode: saved.themeMode === 'light' ? 'light' as const : 'dark' as const,
            notificationsEnabled: typeof saved.notificationsEnabled === 'boolean' ? saved.notificationsEnabled : defaults.notificationsEnabled
          };
          currentPrefs.current = next;
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
    const next = { ...currentPrefs.current, ...patch };
    currentPrefs.current = next;
    setPrefs(next);
    writes.current = writes.current.then(() => AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next)))
      .then(() => setStorageError(null))
      .catch(() => setStorageError('This preference changed for now but could not be saved on this device. Try again.'));
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
      resetPreferences: async () => {
        if (!ready) throw new Error('Device preferences are still loading.');
        const task = writes.current.then(() => AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(defaults)));
        writes.current = task.catch(() => {});
        await task;
        applyTheme(defaults.themeMode);
        currentPrefs.current = defaults;
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
