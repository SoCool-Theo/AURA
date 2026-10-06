import { useEffect, useRef, useState } from 'react';
import { getAssetOutlook, getPortfolioOutlook } from '../../api/forecastingApi';
import { useAuth } from '../../auth/useAuth';
import type { OutlookResponse } from '../../types/forecasting';
import { validOutlookResponse } from './forecastingUi';

export function useForecasting(scope: 'portfolio' | 'asset', selection: string) {
  const { user, status } = useAuth();
  const account = status === 'authenticated' ? user?.id : undefined;
  const identity = `${account ?? ''}:${scope}:${selection}`;
  const identityRef = useRef(identity); identityRef.current = identity;
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState<{ identity: string; result: OutlookResponse | null; loading: boolean; error: unknown }>({ identity: '', result: null, loading: false, error: null });

  useEffect(() => {
    if (!account || !selection) return;
    const controller = new AbortController();
    const current = () => !controller.signal.aborted && identityRef.current === identity;
    // Clear old estimates, including on refresh; never label previous results current.
    setState({ identity, result: null, loading: true, error: null });
    const timeout = setTimeout(() => {
      if (current()) setState({ identity, result: null, loading: false, error: new Error('Outlook timed out') });
      controller.abort();
    }, 60000);
    const request = scope === 'asset'
      ? getAssetOutlook(selection, { signal: controller.signal })
      : getPortfolioOutlook(selection, { signal: controller.signal });
    void request.then(result => {
      if (!current()) return;
      if (!validOutlookResponse(result, scope, selection)) {
        throw new Error('Invalid outlook response');
      }
      setState({ identity, result, loading: false, error: null });
    }).catch(error => {
      if (current()) setState({ identity, result: null, loading: false, error });
    }).finally(() => clearTimeout(timeout));
    return () => { clearTimeout(timeout); controller.abort(); };
  }, [account, identity, scope, selection, revision]);

  const visible = state.identity === identity && account && selection ? state : null;
  return {
    result: visible?.result ?? null,
    loading: Boolean(account && selection && (!visible || visible.loading)),
    error: visible?.error ?? null,
    refresh: () => setRevision(value => value + 1),
  };
}
