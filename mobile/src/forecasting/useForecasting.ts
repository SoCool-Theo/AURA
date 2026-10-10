import { useCallback, useRef, useState } from 'react';
import { useFocusEffect } from '@react-navigation/native';
import { getAssetOutlook, getPortfolioOutlook, getWeeklyAssetOutlook, getWeeklyPortfolioOutlook } from '../api/forecastingApi';
import { useAuth } from '../auth/useAuth';
import type { ForecastHorizon, OutlookResponse } from '../types/forecasting';
import { forecastHorizons, validOutlookResponse } from './forecastingUi';

export function useForecasting(scope: 'portfolio' | 'asset', selection: string, horizon: ForecastHorizon = 30, compare = false) {
  const { user, status } = useAuth();
  const account = status === 'authenticated' ? user?.id : undefined;
  const requestedHorizon = compare ? null : horizon;
  const identity = `${account ?? ''}:${scope}:${selection}:${requestedHorizon ?? 'all'}`;
  const identityRef = useRef(identity); identityRef.current = identity;
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState<{
    identity: string; outlooks: OutlookResponse[]; pending: ForecastHorizon[];
    errors: Partial<Record<ForecastHorizon, unknown>>;
  }>({ identity: '', outlooks: [], pending: [], errors: {} });

  useFocusEffect(useCallback(() => {
    if (!account || !selection) return;
    const requested = requestedHorizon === null ? [...forecastHorizons] : [requestedHorizon];
    // Clear every old estimate on refresh or selection change; no cached prediction fallback.
    setState({ identity, outlooks: [], pending: requested, errors: {} });
    const cleanups = requested.map(days => {
      const controller = new AbortController();
      const current = () => !controller.signal.aborted && identityRef.current === identity;
      const finish = (result: OutlookResponse | null, error: unknown = null) => {
        if (!current()) return;
        setState(previous => previous.identity !== identity ? previous : {
          ...previous,
          outlooks: result ? [...previous.outlooks, result].sort((a, b) => a.horizon_days - b.horizon_days) : previous.outlooks,
          pending: previous.pending.filter(day => day !== days),
          errors: error ? { ...previous.errors, [days]: error } : previous.errors,
        });
      };
      const timeout = setTimeout(() => {
        finish(null, new Error('Outlook timed out'));
        controller.abort();
      }, 60000);
      const options = { signal: controller.signal };
      const request = days === 30
        ? scope === 'asset' ? getAssetOutlook(selection, options) : getPortfolioOutlook(selection, options)
        : scope === 'asset' ? getWeeklyAssetOutlook(selection, days, options) : getWeeklyPortfolioOutlook(selection, days, options);
      void request.then(result => {
        if (!current()) return;
        if (!validOutlookResponse(result, scope, selection, days)) throw new Error('Invalid outlook response');
        finish(result);
      }).catch(error => finish(null, error)).finally(() => clearTimeout(timeout));
      return () => { clearTimeout(timeout); controller.abort(); };
    });
    return () => cleanups.forEach(cleanup => cleanup());
  }, [account, identity, scope, selection, requestedHorizon, revision]));

  const visible = state.identity === identity && account && selection ? state : null;
  return {
    result: visible?.outlooks.find(result => result.horizon_days === horizon) ?? null,
    loading: Boolean(account && selection && (!visible || visible.pending.includes(horizon))),
    error: visible?.errors[horizon] ?? null,
    outlooks: visible?.outlooks ?? [],
    comparisonLoading: Boolean(visible?.pending.length),
    unavailableHorizons: forecastHorizons.filter(day => visible && Object.hasOwn(visible.errors, day)),
    refresh: () => setRevision(value => value + 1),
  };
}
