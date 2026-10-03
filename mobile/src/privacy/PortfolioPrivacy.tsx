import AsyncStorage from '@react-native-async-storage/async-storage';
import React, { createContext, useContext, useEffect, useRef, useState, type PropsWithChildren } from 'react';
import { useAuth } from '../auth/useAuth';

type Privacy = {
  hideValues: boolean;
  ready: boolean;
  storageError: string | null;
  setHideValues: (hidden: boolean) => void;
};
const defaults: Privacy = { hideValues: false, ready: true, storageError: null, setHideValues: () => {} };
const PrivacyContext = createContext(defaults);
export const privacyStorageKey = (accountId: string) => `aura_portfolio_privacy_v1:${encodeURIComponent(accountId)}`;
export const HIDDEN_VALUE = '••••';

function AccountPrivacy({ accountId, children }: PropsWithChildren<{ accountId: string }>) {
  const key = privacyStorageKey(accountId);
  // Hide immediately while async storage loads, so a remembered On never flashes Off.
  const [hideValues, setHidden] = useState(true);
  const [ready, setReady] = useState(false);
  const [storageError, setStorageError] = useState<string | null>(null);
  const writes = useRef(Promise.resolve());
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    let cancelled = false;
    void (async () => {
      try {
        const raw = await AsyncStorage.getItem(key);
        const saved: unknown = raw === null ? false : JSON.parse(raw);
        if (typeof saved !== 'boolean') throw new Error('Invalid preference');
        if (!cancelled) setHidden(saved);
      } catch {
        if (!cancelled) setStorageError('Privacy preferences could not be loaded. Values are hidden for now. Choose a setting to retry saving.');
      } finally {
        if (!cancelled) setReady(true);
      }
    })();
    return () => { cancelled = true; mounted.current = false; };
  }, [key]);
  function setHideValues(hidden: boolean) {
    if (!ready) return;
    setHidden(hidden);
    // Serialize writes so rapid toggles persist the last choice in order.
    writes.current = writes.current.then(() => AsyncStorage.setItem(key, JSON.stringify(hidden)))
      .then(() => { if (mounted.current) setStorageError(null); })
      .catch(() => { if (mounted.current) setStorageError('This choice applies now but could not be saved on this device. Try again.'); });
  }
  return <PrivacyContext.Provider value={{ hideValues, ready, storageError, setHideValues }}>{children}</PrivacyContext.Provider>;
}

export function PortfolioPrivacyProvider({ children }: PropsWithChildren) {
  const { user } = useAuth();
  return user ? <AccountPrivacy key={user.id} accountId={user.id}>{children}</AccountPrivacy>
    : <PrivacyContext.Provider value={defaults}>{children}</PrivacyContext.Provider>;
}

export const usePortfolioPrivacy = () => useContext(PrivacyContext);
export function usePrivateValue() {
  const { hideValues } = usePortfolioPrivacy();
  return (value: string) => hideValues ? HIDDEN_VALUE : value;
}
export function usePrivateText() {
  const { hideValues } = usePortfolioPrivacy();
  return (text: string) => hideValues
    ? text.replace(/(?:[+−-]?[$฿]\s*\d(?:[\d,.]*\d)?|\b(?:USD|THB)\s*\d(?:[\d,.]*\d)?)/g, HIDDEN_VALUE)
    : text;
}
