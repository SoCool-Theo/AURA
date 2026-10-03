import { createContext, useContext, useState, type ReactNode } from 'react';
import { useAuth } from '../auth/useAuth';

type Privacy = {
  hideValues: boolean;
  ready: boolean;
  storageError: string | null;
  setHideValues: (hidden: boolean) => void;
  resetPrivacy: () => Promise<void>;
};
const defaults: Privacy = { hideValues: false, ready: true, storageError: null, setHideValues: () => {}, resetPrivacy: async () => {} };
const PrivacyContext = createContext(defaults);
export const privacyStorageKey = (accountId: string) => `aura_portfolio_privacy_v1:${encodeURIComponent(accountId)}`;
export const HIDDEN_VALUE = '••••';

function AccountPrivacy({ accountId, children }: { accountId: string; children: ReactNode }) {
  const key = privacyStorageKey(accountId);
  const [state, setState] = useState(() => {
    try {
      const raw = localStorage.getItem(key);
      if (raw === null) return { hideValues: false, storageError: null };
      const saved: unknown = JSON.parse(raw);
      if (typeof saved !== 'boolean') throw new Error('Invalid preference');
      return { hideValues: saved, storageError: null };
    } catch {
      // Fail closed rather than expose balances when a saved choice cannot be read.
      return { hideValues: true, storageError: 'Privacy preferences could not be loaded. Values are hidden for now. Choose a setting to retry saving.' };
    }
  });
  function setHideValues(hidden: boolean) {
    let storageError: string | null = null;
    try { localStorage.setItem(key, JSON.stringify(hidden)); }
    catch { storageError = 'This choice applies now but could not be saved in this browser. Try again.'; }
    setState({ hideValues: hidden, storageError });
  }
  async function resetPrivacy() {
    try {
      localStorage.setItem(key, 'false');
      setState({ hideValues: false, storageError: null });
    } catch (error) {
      setState(previous => ({ ...previous, storageError: 'Privacy preferences could not be reset. Try again.' }));
      throw error;
    }
  }
  return <PrivacyContext.Provider value={{ ...state, ready: true, setHideValues, resetPrivacy }}>{children}</PrivacyContext.Provider>;
}

export function PortfolioPrivacyProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  // Remount only when account ID changes; logout never removes saved preferences.
  return user ? <AccountPrivacy key={user.id} accountId={user.id}>{children}</AccountPrivacy>
    : <PrivacyContext.Provider value={defaults}>{children}</PrivacyContext.Provider>;
}

export const usePortfolioPrivacy = () => useContext(PrivacyContext);
export function usePrivateValue() {
  const { hideValues } = usePortfolioPrivacy();
  return (value: string) => hideValues ? HIDDEN_VALUE : value;
}

// For deterministic metric explanations only, not arbitrary AI prose.
export function usePrivateText() {
  const { hideValues } = usePortfolioPrivacy();
  return (text: string) => hideValues
    ? text.replace(/(?:[+−-]?[$฿]\s*\d(?:[\d,.]*\d)?|\b(?:USD|THB)\s*\d(?:[\d,.]*\d)?)/g, HIDDEN_VALUE)
    : text;
}
