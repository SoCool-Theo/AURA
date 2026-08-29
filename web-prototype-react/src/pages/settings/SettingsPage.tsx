import { useAuth } from '../../auth/useAuth';
import { usePersistedState } from '../../hooks/usePersistedState';
import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import styles from '../DeferredFeature.module.css';

type LocalPreferences = { language: string; timezone: string };
const DEFAULT_PREFERENCES: LocalPreferences = { language: 'English', timezone: 'UTC+07:00 Bangkok' };

export function SettingsPage() {
  const { user } = useAuth();
  const [preferences, setPreferences] = usePersistedState<LocalPreferences>('aura-ui-preferences', DEFAULT_PREFERENCES);
  return <div className={`page ${styles.page}`}><header className={styles.header}><span>ACCOUNT AND LOCAL PREFERENCES</span><h1>Settings</h1><p>Review the authenticated account and configure clearly local interface preferences.</p></header><Card className={styles.card}><span className={styles.icon}><Icon name="settings" size={28} /></span><span className={styles.badge}>Account profile is read-only</span><h2>{user?.email ?? 'Authenticated Aura account'}</h2><p>The current backend supports reading the authenticated account only. Email, display name, phone, profile photo, and password changes are unavailable and are not simulated in the browser.</p><div className={styles.preferenceGrid}><label>Preferred language<select value={preferences.language} onChange={event => setPreferences(current => ({ ...current, language: event.target.value }))}><option>English</option><option>Thai</option></select></label><label>Preferred timezone<select value={preferences.timezone} onChange={event => setPreferences(current => ({ ...current, timezone: event.target.value }))}><option>UTC+06:30 Yangon</option><option>UTC+07:00 Bangkok</option></select></label></div><p className={styles.localNote}>These choices are saved only in this browser and do not update the Aura account. Translations and timezone-based date formatting are not implemented yet.</p></Card></div>;
}
