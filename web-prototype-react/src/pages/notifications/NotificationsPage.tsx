import { useEffect } from 'react';
import { go } from '../../app/routes';
import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import { ConfirmationDialog } from '../../components/ui/ConfirmationDialog';
import { notificationPreferenceRows, useNotificationCenter } from '../../notifications/useNotifications';
import { watchNotificationForeground } from '../../notifications/notificationForeground';
import styles from './NotificationsPage.module.css';

export function NotificationsPage({ settings = false }: { settings?: boolean }) {
  const center = useNotificationCenter(settings);
  const disabled = center.loading || center.busy;
  useEffect(() => { window.scrollTo({ top: 0 }); }, [settings]);
  useEffect(() => { if (!settings) return watchNotificationForeground(() => { if (!center.busy) void center.refresh(); }); }, [settings, center.refresh, center.busy]);
  return <div className={`page ${styles.page}`} aria-busy={disabled}>
    <button className={styles.back} type="button" onClick={() => go(settings ? 'settings' : 'dashboard')}>← Back to {settings ? 'Settings' : 'Dashboard'}</button>
    <header className={styles.header}>
      <div><span className={styles.eyebrow}>AURA UPDATES</span><h1>{settings ? 'App notifications' : 'Notifications'}</h1>
        <p>{settings ? 'Choose which updates you receive inside Aura.' : 'Your saved analysis and simulation updates, newest first.'}</p></div>
      <button className="secondary-btn" type="button" onClick={() => go(settings ? 'notifications' : 'notification-settings')}>{settings ? 'Open inbox' : 'Notification settings'}</button>
    </header>
    {center.error && <Card className={styles.error}><p role="alert">{center.error}</p><button className="secondary-btn" type="button" disabled={disabled} onClick={() => void center.refresh()}>Retry / refresh</button></Card>}
    {center.notice && <p className={styles.notice} role="status">{center.notice}</p>}
    {center.loading && <p className={styles.helper} role="status">Loading notifications…</p>}
    {settings && center.prefs && <Card className={styles.preferences}>
      {notificationPreferenceRows.map(row => <button key={row.key} type="button" className={styles.preference}
        role="switch" aria-checked={center.prefs![row.key]} aria-label={row.title}
        disabled={disabled || (row.key !== 'enabled' && !center.prefs!.enabled)}
        onClick={() => void center.toggle(row.key, !center.prefs![row.key])}>
        <span><strong>{row.title}</strong><span className={styles.helper}>{row.description}</span></span>
        <span className={`${styles.switch} ${center.prefs![row.key] ? styles.on : ''}`} aria-hidden="true"><i /></span>
      </button>)}
      <p className={styles.helper}>Remembered for your account on web and mobile, including after signing out. Turning this off stops future notifications; existing messages stay in your inbox. Reset local data does not change these account preferences.</p>
      <p className={styles.helper}>Phone push, browser push, email notifications, and price alerts are not enabled.</p>
    </Card>}
    {!settings && center.feed && <>
      <div className={styles.toolbar}><p className={styles.helper} role="status">{center.feed.unread_count} unread · {center.feed.total} total</p>
        <div><button type="button" className="secondary-btn" disabled={disabled} onClick={() => void center.refresh()}>Refresh</button>
          <button type="button" className="secondary-btn" disabled={disabled || !center.feed.unread_count} onClick={() => void center.markAll()}>Mark all as read</button>
          <button type="button" className={`${styles.link} ${styles.danger}`} disabled={disabled || !center.feed.total} onClick={() => center.requestClear('all')}>Clear all notifications</button></div></div>
      {center.feed.items.length === 0 ? <Card className={styles.empty}><Icon name="bell" size={32} /><h2>You’re all caught up</h2>
        <p>New analysis reports and saved simulations will appear here when notifications are enabled. Older results are not added automatically.</p></Card>
        : <ul className={styles.list}>{center.feed.items.map(item => <li key={item.id}>
          <Card className={`${styles.item} ${item.read_at ? '' : styles.unread}`}>
            <span className={styles.icon}><Icon name={item.kind === 'analysis' ? 'reports' : 'simulations'} size={22} /></span>
            <div className={styles.copy}><h2>{item.title} {!item.read_at && <span className={styles.badge}>Unread</span>}</h2>
              <p>{item.message}</p><time className={styles.helper} dateTime={item.created_at}>{new Date(item.created_at).toLocaleString()}</time></div>
            <div className={styles.actions}>
              <button className="secondary-btn" type="button" disabled={disabled} onClick={() => void center.open(item, () => go(`${item.kind === 'analysis' ? 'reports' : 'simulations'}/${encodeURIComponent(item.portfolio_id)}/${encodeURIComponent(item.resource_id)}`))}>View {item.kind === 'analysis' ? 'report' : 'simulation'} →</button>
              {!item.read_at && <button className={styles.link} type="button" disabled={disabled} onClick={() => void center.markRead(item)}>Mark as read</button>}
              <button className={`${styles.link} ${styles.danger}`} type="button" disabled={disabled} onClick={() => center.requestClear(item)}>Clear notification</button>
            </div>
          </Card>
        </li>)}</ul>}
      <div className={styles.pagination}><button className="secondary-btn" type="button" disabled={disabled || center.offset === 0} onClick={center.previous}>Previous</button>
        <span className={styles.helper}>Page {Math.floor(center.offset / 25) + 1}</span>
        <button className="secondary-btn" type="button" disabled={disabled || center.offset + center.feed.items.length >= center.feed.total || center.offset >= 10000} onClick={center.next}>Next</button></div>
    </>}
    {center.clearTarget && <ConfirmationDialog title={center.clearTarget === 'all' ? 'Clear all notifications?' : 'Clear notification?'}
      tone="danger" description="This permanently removes the selected notification messages from your account’s inbox on web and mobile. Your portfolios, reports, simulations, and notification preferences stay unchanged. This cannot be undone."
      subject={center.clearTarget === 'all' ? 'All notifications, including other pages' : center.clearTarget.title}
      subjectLabel="NOTIFICATIONS ONLY" confirmLabel={center.clearTarget === 'all' ? 'Clear all notifications' : 'Clear notification'}
      busy={center.busy} onCancel={center.cancelClear} onConfirm={() => void center.confirmClear()}>
      {center.error && <p className={styles.error} role="alert">{center.error}</p>}
    </ConfirmationDialog>}
  </div>;
}
