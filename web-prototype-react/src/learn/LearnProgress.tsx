import { createContext, useContext, useState, type ReactNode } from 'react';
import { useAuth } from '../auth/useAuth';

export const learnProgressStorageKey = (accountId: string) => `aura_learn_progress_v2:${encodeURIComponent(accountId)}`;
type Progress = {
  learnProgress: Record<string, boolean>;
  localError: string | null;
  toggleLessonComplete: (lessonId: string) => void;
  retryLocalData: () => void;
  resetLocalData: () => Promise<void>;
};
const defaults: Progress = { learnProgress: {}, localError: null, toggleLessonComplete: () => {}, retryLocalData: () => {}, resetLocalData: async () => {} };
const LearnProgressContext = createContext(defaults);

function AccountProgress({ accountId, children }: { accountId: string; children: ReactNode }) {
  const key = learnProgressStorageKey(accountId);
  function read(): Pick<Progress, 'learnProgress' | 'localError'> {
    try {
      const raw = localStorage.getItem(key);
      const value: unknown = raw === null ? {} : JSON.parse(raw);
      if (!value || typeof value !== 'object' || Array.isArray(value)
        || Object.values(value).some(item => typeof item !== 'boolean')) throw new Error('Invalid Learn progress');
      return { learnProgress: value as Record<string, boolean>, localError: null };
    } catch {
      return { learnProgress: {}, localError: 'Learn progress could not be loaded. Retry or reset local data in Settings.' };
    }
  }
  const [state, setState] = useState(read);
  function toggleLessonComplete(lessonId: string) {
    if (state.localError) return;
    const next = { ...state.learnProgress, [lessonId]: !state.learnProgress[lessonId] };
    try {
      localStorage.setItem(key, JSON.stringify(next));
      setState({ learnProgress: next, localError: null });
    } catch {
      setState(previous => ({ ...previous, localError: 'Learn progress could not be saved. Retry loading before editing again.' }));
    }
  }
  async function resetLocalData() {
    localStorage.removeItem(key);
    setState({ learnProgress: {}, localError: null });
  }
  return <LearnProgressContext.Provider value={{ ...state, toggleLessonComplete, retryLocalData: () => setState(read()), resetLocalData }}>{children}</LearnProgressContext.Provider>;
}

export function LearnProgressProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  return user ? <AccountProgress key={user.id} accountId={user.id}>{children}</AccountProgress>
    : <LearnProgressContext.Provider value={defaults}>{children}</LearnProgressContext.Provider>;
}
export const useLearnProgress = () => useContext(LearnProgressContext);
