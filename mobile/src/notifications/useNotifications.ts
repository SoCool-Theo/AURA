import { useCallback, useEffect, useRef, useState } from 'react';
import { notificationsApi, notificationsChanged, subscribeNotifications } from '../api/notificationsApi';
import { useAuth } from '../auth/useAuth';
import { watchNotificationForeground } from './notificationForeground';
import type { NotificationItem, NotificationList, NotificationPreferences } from '../types/notification';

export const notificationPreferenceRows = [
  { key: 'enabled', title: 'In-app notifications', description: 'Receive notifications inside Aura. This does not enable phone or browser push.' },
  { key: 'analysis_enabled', title: 'Analysis reports', description: 'When a new portfolio analysis report is saved.' },
  { key: 'simulation_enabled', title: 'Saved simulations', description: 'When an allocation, historical scenario, or combined simulation is saved.' },
] as const;

export function useNotificationBadge() {
  const { user, status } = useAuth();
  const id = status === 'authenticated' ? user?.id : undefined;
  const [state, setState] = useState<{ account?: string; count: number | null }>({ count: null });
  useEffect(() => {
    if (!id) return;
    let live = true, pending = false, queued = false;
    const controller = new AbortController();
    const refresh = async () => {
      if (!live) return;
      if (pending) { queued = true; return; }
      pending = true;
      try {
        const result = await notificationsApi.list(0, 1, { signal: controller.signal });
        if (live && !queued) setState({ account: id, count: result.unread_count });
      } catch { if (live) setState({ account: id, count: null }); }
      finally { pending = false; if (queued && live) { queued = false; void refresh(); } }
    };
    const stopForeground = watchNotificationForeground(() => void refresh());
    const stopChanges = subscribeNotifications(() => void refresh());
    void refresh();
    return () => { live = false; controller.abort(); stopForeground(); stopChanges(); };
  }, [id]);
  return state.account === id ? state.count : null;
}

export function useNotificationCenter(settings: boolean) {
  const { user, status } = useAuth();
  const id = status === 'authenticated' ? user?.id : undefined;
  const identity = useRef(id); identity.current = id;
  const mounted = useRef(true), mutation = useRef(false), generation = useRef(0);
  const [state, setState] = useState<{ account?: string; feed?: NotificationList; prefs?: NotificationPreferences }>({});
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true), [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null), [notice, setNotice] = useState<string | null>(null);
  const [clearTarget, setClearTarget] = useState<NotificationItem | 'all' | null>(null);
  const clearAuthorization = useRef<{ account: string; target: NotificationItem | 'all' } | null>(null);
  const current = () => mounted.current && identity.current === id;
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; generation.current++; }; }, []);

  const refresh = useCallback(async () => {
    if (!id) return;
    const run = ++generation.current;
    setLoading(true); setError(null);
    try {
      if (settings) {
        const prefs = await notificationsApi.preferences();
        if (mounted.current && identity.current === id && run === generation.current) setState({ account: id, prefs });
      } else {
        const feed = await notificationsApi.list(offset);
        if (mounted.current && identity.current === id && run === generation.current) {
          setState({ account: id, feed });
          // A deletion can empty the last page. Return to the beginning safely.
          if (!feed.items.length && offset > 0) setOffset(0);
        }
      }
    } catch {
      if (mounted.current && identity.current === id && run === generation.current) setError('Notifications could not be loaded. Check your connection and try again.');
    } finally { if (mounted.current && identity.current === id && run === generation.current) setLoading(false); }
  }, [id, settings, offset]);

  useEffect(() => { mutation.current = false; clearAuthorization.current = null; setClearTarget(null); setBusy(false); setOffset(0); setNotice(null); setError(null); }, [id, settings]);
  useEffect(() => { void refresh(); return () => { generation.current++; }; }, [refresh]);

  const runMutation = async (operation: () => Promise<void>, success?: () => void) => {
    if (!id || mutation.current || !current()) return;
    mutation.current = true; setBusy(true); setError(null); setNotice(null);
    try {
      await operation();
      if (!current()) return;
      notificationsChanged();
      await refresh();
      if (current()) success?.();
    } catch {
      if (current()) setError('The change could not be confirmed. Refresh to check the current status, then try again.');
    } finally { if (current()) { mutation.current = false; setBusy(false); } }
  };
  const visible = state.account === id ? state : {};
  return {
    feed: visible.feed, prefs: visible.prefs, loading, busy, error, notice, offset,
    clearTarget: clearAuthorization.current?.account === id ? clearTarget : null,
    requestClear: (target: NotificationItem | 'all') => {
      if (loading || mutation.current || !id || !current()) return;
      clearAuthorization.current = { account: id, target }; setClearTarget(target); setError(null);
    },
    cancelClear: () => {
      if (mutation.current) return;
      clearAuthorization.current = null; setClearTarget(null); setError(null);
    },
    confirmClear: () => {
      const authorization = clearAuthorization.current;
      if (!authorization || authorization.account !== id) return Promise.resolve();
      const target = authorization.target;
      return runMutation(async () => {
        if (target === 'all') await notificationsApi.clearAll();
        else {
          try { await notificationsApi.clear(target.id); }
          catch (failure) {
            // Another client may already have cleared this owned inbox entry.
            if (!failure || typeof failure !== 'object' || !('status' in failure) || failure.status !== 404) throw failure;
          }
        }
      }, () => {
        clearAuthorization.current = null; setClearTarget(null);
        setNotice(target === 'all' ? 'All notifications cleared. Your saved results are unchanged.' : 'Notification cleared. Your saved result is unchanged.');
      });
    },
    refresh,
    next: () => { if (!loading && !busy) setOffset(value => value + 25); },
    previous: () => { if (!loading && !busy) setOffset(value => Math.max(0, value - 25)); },
    markAll: () => runMutation(() => notificationsApi.markAllRead()),
    markRead: (item: NotificationItem) => runMutation(() => notificationsApi.markRead(item.id)),
    open: (item: NotificationItem, navigate: () => void) => runMutation(async () => {
      if (!item.read_at) await notificationsApi.markRead(item.id);
    }, navigate),
    toggle: (key: keyof NotificationPreferences, value: boolean) => {
      if (!visible.prefs) return Promise.resolve();
      return runMutation(async () => {
        const prefs = await notificationsApi.savePreferences({ ...visible.prefs!, [key]: value });
        if (current()) setState({ account: id, prefs });
      },
        () => setNotice('Notification preferences saved to your account.'));
    },
  };
}
