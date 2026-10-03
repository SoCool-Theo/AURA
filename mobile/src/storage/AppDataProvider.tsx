import React, { createContext, PropsWithChildren, useCallback, useEffect, useRef, useState } from 'react';
import { clearLocalAuraData, loadLearnProgress, saveLearnProgress } from './appStorage';
import { useAuth } from '../auth/useAuth';

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
  const { user } = useAuth();
  return <AccountAppData key={user?.id ?? 'signed-out'} accountId={user?.id ?? null}>{children}</AccountAppData>;
}

function AccountAppData({ accountId, children }: PropsWithChildren<{ accountId: string | null }>) {
  const [loading, setLoading] = useState(true);
  const [learnProgress, setLearnProgress] = useState<Record<string, boolean>>({});
  const [localError, setLocalError] = useState<string | null>(null);
  const [localPending, setLocalPending] = useState(false);
  const pendingRef = useRef(false);
  const generation = useRef(0);

  const retryLocalData = useCallback(async () => {
    if (pendingRef.current) return;
    const request = ++generation.current;
    setLoading(true);
    try {
      const progress = accountId ? await loadLearnProgress(accountId) : {};
      if (request !== generation.current) return;
      setLearnProgress(progress);
      setLocalError(null);
    } catch {
      if (request !== generation.current) return;
      setLocalError('Could not read device-local Learn progress. Retry or reset local data in Settings.');
    } finally {
      if (request === generation.current) setLoading(false);
    }
  }, [accountId]);
  useEffect(() => { void retryLocalData(); return () => { generation.current++; }; }, [retryLocalData]);

  async function toggleLessonComplete(lessonId: string) {
    if (!accountId || pendingRef.current || loading || localError) return;
    pendingRef.current = true;
    setLocalPending(true);
    try {
      const next = { ...learnProgress, [lessonId]: !learnProgress[lessonId] };
      await saveLearnProgress(accountId, next);
      setLearnProgress(next);
    } catch {
      setLocalError('Could not save Learn progress on this device. Retry loading before editing again.');
    } finally {
      pendingRef.current = false;
      setLocalPending(false);
    }
  }

  async function resetLocalData() {
    if (!accountId || pendingRef.current) throw new Error('Local data is unavailable or busy.');
    pendingRef.current = true;
    setLocalPending(true);
    generation.current++;
    try {
      await clearLocalAuraData(accountId);
      setLearnProgress({});
      setLocalError(null);
    } finally {
      pendingRef.current = false;
      setLocalPending(false);
      setLoading(false);
    }
  }

  return <AppDataContext.Provider value={{ loading, localError, localPending, learnProgress, retryLocalData, toggleLessonComplete, resetLocalData }}>{children}</AppDataContext.Provider>;
}
