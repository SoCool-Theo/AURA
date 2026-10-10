import { useCallback, useRef, useState, useEffect } from 'react';
import { useAuth } from '../auth/useAuth';
import { getMarketDataStatus } from '../api/marketDataApi';
import { watchMarketDataForeground } from './marketDataForeground';
import type { MarketDataStatusResponse } from '../types/marketData';

export function useMarketDataRefresh(onRefresh: () => void, enabled = true) {
  const { user, status: authentication } = useAuth();
  const account = authentication === 'authenticated' ? user?.id : undefined;
  const identity = useRef(account); identity.current = account;
  const callback = useRef(onRefresh); callback.current = onRefresh;
  const action = useRef<(() => void) | null>(null);
  const [state, setState] = useState<{ account?: string; status: MarketDataStatusResponse | null; unavailable: boolean; refreshing: boolean }>({ status: null, unavailable: false, refreshing: false });

  useEffect(() => {
    if (!account || !enabled) return;
    type Read = { controller: AbortController; timeout?: ReturnType<typeof setTimeout> };
    let live = true, active = false, request: Read | null = null;
    const cancel = () => { if (request) { clearTimeout(request.timeout); request.controller.abort(); request = null; } };
    const refresh = async (reloadPrices = true) => {
      if (!live || !active || request || identity.current !== account) return;
      const controller = new AbortController();
      const read: Read = { controller }; request = read;
      const current = () => live && !controller.signal.aborted && identity.current === account;
      setState(previous => ({ account, status: previous.account === account ? previous.status : null, unavailable: previous.account === account && previous.unavailable, refreshing: true }));
      if (reloadPrices) callback.current();
      const timeout = setTimeout(() => {
        if (current()) setState({ account, status: null, unavailable: true, refreshing: false });
        controller.abort();
        if (request === read) request = null;
      }, 20000);
      read.timeout = timeout;
      try {
        const result = await getMarketDataStatus({ signal: controller.signal });
        if (current()) setState({ account, status: result, unavailable: false, refreshing: false });
      } catch {
        // Never present a previous successful check as current after a failure.
        if (current()) setState({ account, status: null, unavailable: true, refreshing: false });
      } finally {
        clearTimeout(timeout);
        if (request === read) request = null;
      }
    };
    action.current = () => { void refresh(); };
    const stop = watchMarketDataForeground(
      () => { void refresh(); },
      value => {
        active = value;
        if (!active) {
          cancel();
          if (live) setState(previous => ({ ...previous, refreshing: false }));
        }
      },
    );
    // Existing page loaders perform the first price read.
    void refresh(false);
    return () => { live = false; action.current = null; cancel(); stop(); };
  }, [account, enabled]);

  const visible = enabled && account && state.account === account ? state : null;
  return {
    status: visible?.status ?? null,
    unavailable: visible?.unavailable ?? false,
    refreshing: visible?.refreshing ?? false,
    refresh: useCallback(() => action.current?.(), []),
  };
}
