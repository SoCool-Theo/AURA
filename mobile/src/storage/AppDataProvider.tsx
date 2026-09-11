import React, { createContext, PropsWithChildren, useCallback, useEffect, useRef, useState } from 'react';
import { clearLocalAuraData, loadLearnProgress, saveLearnProgress } from './appStorage';

// Device-local educational progress only. All financial/domain data uses API providers.
type ContextValue = {
  loading: boolean;
  localError: string | null;
  localPending: boolean;
  learnProgress: Record<string, boolean>;
  retryLocalData: () => Promise<void>;
  toggleLessonComplete: (lessonId: string) => Promise<void>;
  resetLocalData: () => Promise<void>;
};

export const AppDataContext = createContext<ContextValue | undefined>(undefined);

export function AppDataProvider({ children }: PropsWithChildren) {
  const [loading, setLoading] = useState(true);
  const [learnProgress, setLearnProgress] = useState<Record<string, boolean>>({});
  const [localError, setLocalError] = useState<string | null>(null);
  const [localPending, setLocalPending] = useState(false);
  const pendingRef = useRef(false);

  const retryLocalData = useCallback(async () => {
    setLoading(true);
    try {
      setLearnProgress(await loadLearnProgress());
      setLocalError(null);
    } catch {
      setLocalError('Could not read device-local Learn progress. Retry or reset local data in Settings.');
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { void retryLocalData(); }, [retryLocalData]);

  async function toggleLessonComplete(lessonId: string) {
    if (pendingRef.current || loading || localError) return;
    pendingRef.current = true;
    setLocalPending(true);
    try {
      const next = { ...learnProgress, [lessonId]: !learnProgress[lessonId] };
      await saveLearnProgress(next);
      setLearnProgress(next);
    } catch {
      setLocalError('Could not save Learn progress on this device. Retry loading before editing again.');
    } finally {
      pendingRef.current = false;
      setLocalPending(false);
    }
  }

  async function resetLocalData() {
    await clearLocalAuraData();
    setLearnProgress({});
    setLocalError(null);
  }

  return <AppDataContext.Provider value={{ loading, localError, localPending, learnProgress, retryLocalData, toggleLessonComplete, resetLocalData }}>{children}</AppDataContext.Provider>;
}
