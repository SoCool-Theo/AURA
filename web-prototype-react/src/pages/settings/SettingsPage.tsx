import { useEffect, useMemo, useState } from 'react';
import { changeCurrentUserPassword, updateCurrentUserProfile } from '../../api/authApi';
import { apiErrorPresentation, apiValidationIssues } from '../../api/apiErrorPresentation';
import { ApiError } from '../../api/apiClient';
import { useAuth } from '../../auth/useAuth';
import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import type {
  AuthenticatedUserResponse,
  PreferredLanguage,
  ProfileTimezone,
  ProfileUpdateRequest,
} from '../../types/auth';
import styles from './SettingsPage.module.css';

type ProfileDraft = {
  displayName: string;
  email: string;
  phoneNumber: string;
  language: PreferredLanguage;
  timezone: ProfileTimezone;
  currentPassword: string;
};

const EMPTY_PROFILE: ProfileDraft = {
  displayName: '',
  email: '',
  phoneNumber: '',
  language: 'en',
  timezone: 'Asia/Bangkok',
  currentPassword: '',
};

function draftFromUser(user: AuthenticatedUserResponse | null): ProfileDraft {
  if (!user) return EMPTY_PROFILE;
  return {
    displayName: user.display_name ?? '',
    email: user.email,
    phoneNumber: user.phone_number ?? '',
    language: user.preferred_language,
    timezone: user.timezone,
    currentPassword: '',
  };
}

function profileRequestError(error: unknown, fallback: string): string {
  if (error instanceof ApiError && error.status === 403) {
    return 'The current password is incorrect.';
  }
  if (error instanceof ApiError && error.status === 409) {
    return 'That email address is already used by another Aura account.';
  }
  const issues = apiValidationIssues(error);
  if (issues.length) return issues.map(issue => issue.message).join('. ');
  return apiErrorPresentation(error, { fallbackMessage: fallback }).message;
}

function validateProfile(draft: ProfileDraft): string | null {
  const name = draft.displayName.trim();
  const phone = draft.phoneNumber.trim();
  const email = draft.email.trim();
  if (name.length > 100) return 'Display name must be 100 characters or fewer.';
  if (!email) return 'Email address is required.';
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return 'Enter a valid email address.';
  if (phone && (phone.length < 4 || phone.length > 32 || !/^[+().\-\d\s]+$/.test(phone))) {
    return 'Phone number must be 4–32 characters and use only numbers, spaces, +, parentheses, periods, or hyphens.';
  }
  return null;
}

export function SettingsPage() {
  const { user, setCurrentUser } = useAuth();
  const [profile, setProfile] = useState<ProfileDraft>(() => draftFromUser(user));
  const [profilePending, setProfilePending] = useState(false);
  const [profileMessage, setProfileMessage] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [passwords, setPasswords] = useState({ current: '', next: '', confirm: '' });
  const [passwordPending, setPasswordPending] = useState(false);
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  useEffect(() => {
    setProfile(draftFromUser(user));
  }, [user]);

  const emailChanged = Boolean(user && profile.email.trim().toLowerCase() !== user.email);
  const initials = useMemo(() => {
    const source = profile.displayName.trim() || profile.email.trim() || 'Aura';
    const parts = source.split(/\s+/).filter(Boolean);
    return (parts.length > 1 ? `${parts[0][0]}${parts.at(-1)?.[0] ?? ''}` : source.slice(0, 2)).toUpperCase();
  }, [profile.displayName, profile.email]);

  async function saveProfile(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!user || profilePending) return;
    setProfileMessage(null);
    const localError = validateProfile(profile);
    if (localError) {
      setProfileError(localError);
      return;
    }
    if (emailChanged && !profile.currentPassword) {
      setProfileError('Enter your current password to change the account email.');
      return;
    }

    const displayName = profile.displayName.trim() || null;
    const phoneNumber = profile.phoneNumber.trim() || null;
    const email = profile.email.trim().toLowerCase();
    const request: ProfileUpdateRequest = {};
    if (displayName !== user.display_name) request.display_name = displayName;
    if (phoneNumber !== user.phone_number) request.phone_number = phoneNumber;
    if (profile.language !== user.preferred_language) request.preferred_language = profile.language;
    if (profile.timezone !== user.timezone) request.timezone = profile.timezone;
    if (email !== user.email) {
      request.email = email;
      request.current_password = profile.currentPassword;
    }
    if (Object.keys(request).length === 0) {
      setProfileError(null);
      setProfileMessage('Your profile is already up to date.');
      return;
    }

    setProfilePending(true);
    setProfileError(null);
    try {
      const updatedUser = await updateCurrentUserProfile(request);
      setCurrentUser(updatedUser);
      setProfileMessage('Profile changes saved.');
    } catch (error) {
      setProfileError(profileRequestError(error, 'Aura could not save your profile. Please try again.'));
    } finally {
      setProfilePending(false);
    }
  }

  async function savePassword(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (passwordPending) return;
    setPasswordMessage(null);
    if (!passwords.current) {
      setPasswordError('Enter your current password.');
      return;
    }
    if (passwords.next.length < 8) {
      setPasswordError('New password must be at least 8 characters.');
      return;
    }
    if (passwords.current === passwords.next) {
      setPasswordError('Choose a new password that differs from the current password.');
      return;
    }
    if (passwords.next !== passwords.confirm) {
      setPasswordError('New password and confirmation do not match.');
      return;
    }

    setPasswordPending(true);
    setPasswordError(null);
    try {
      await changeCurrentUserPassword({
        current_password: passwords.current,
        new_password: passwords.next,
      });
      setPasswords({ current: '', next: '', confirm: '' });
      setPasswordMessage('Password changed successfully.');
    } catch (error) {
      setPasswordError(profileRequestError(error, 'Aura could not change your password. Please try again.'));
    } finally {
      setPasswordPending(false);
    }
  }

  return (
    <div className={`page ${styles.page}`}>
      <header className={styles.header}>
        <span>ACCOUNT SETTINGS</span>
        <h1>Profile & security</h1>
        <p>Manage the account information Aura stores for your signed-in profile.</p>
      </header>

      <Card className={styles.identityCard}>
        <div className={styles.avatar} aria-hidden="true">{initials}</div>
        <div>
          <span className={styles.eyebrow}>SIGNED-IN ACCOUNT</span>
          <h2>{user?.display_name || 'Aura Investor'}</h2>
          <p>{user?.email}</p>
        </div>
        <span className={styles.secureBadge}><Icon name="shield" size={15} /> Backend secured</span>
      </Card>

      <div className={styles.columns}>
        <Card className={styles.formCard}>
          <div className={styles.sectionHeading}>
            <span className={styles.sectionIcon}><Icon name="assistant" size={19} /></span>
            <div><h2>Personal information</h2><p>These details follow your Aura account across devices.</p></div>
          </div>
          <form onSubmit={saveProfile}>
            <div className={styles.formGrid}>
              <label>Display name<input value={profile.displayName} maxLength={100} autoComplete="name" onChange={event => setProfile(current => ({ ...current, displayName: event.target.value }))} placeholder="Your name" /></label>
              <label>Email address<input value={profile.email} type="email" autoComplete="email" required onChange={event => setProfile(current => ({ ...current, email: event.target.value }))} placeholder="name@example.com" /></label>
              <label>Phone number <small>Optional</small><input value={profile.phoneNumber} type="tel" maxLength={32} autoComplete="tel" onChange={event => setProfile(current => ({ ...current, phoneNumber: event.target.value }))} placeholder="+66 00 000 0000" /></label>
              <label>Preferred language<select value={profile.language} onChange={event => setProfile(current => ({ ...current, language: event.target.value as PreferredLanguage }))}><option value="en">English</option><option value="th">Thai</option></select></label>
              <label className={styles.fullWidth}>Timezone<select value={profile.timezone} onChange={event => setProfile(current => ({ ...current, timezone: event.target.value as ProfileTimezone }))}><option value="Asia/Bangkok">UTC+07:00 Bangkok</option><option value="Asia/Yangon">UTC+06:30 Yangon</option></select></label>
              {emailChanged && <label className={styles.fullWidth}>Current password <small>Required to change email</small><input value={profile.currentPassword} type="password" autoComplete="current-password" onChange={event => setProfile(current => ({ ...current, currentPassword: event.target.value }))} /></label>}
            </div>
            <p className={styles.fieldNote}>Language and timezone are saved now; translated copy and timezone-based formatting will be applied in a later UI update.</p>
            {profileError && <p className={styles.error} role="alert">{profileError}</p>}
            {profileMessage && <p className={styles.success} role="status">{profileMessage}</p>}
            <div className={styles.actions}>
              <button type="button" className="secondary-btn" disabled={profilePending} onClick={() => { setProfile(draftFromUser(user)); setProfileError(null); setProfileMessage(null); }}>Discard</button>
              <button type="submit" className="primary-btn" disabled={profilePending}>{profilePending ? 'Saving…' : 'Save profile'}</button>
            </div>
          </form>
        </Card>

        <Card className={styles.formCard}>
          <div className={styles.sectionHeading}>
            <span className={`${styles.sectionIcon} ${styles.securityIcon}`}><Icon name="shield" size={19} /></span>
            <div><h2>Change password</h2><p>Confirm your current password before choosing a new one.</p></div>
          </div>
          <form onSubmit={savePassword}>
            <div className={styles.passwordFields}>
              <label>Current password<input value={passwords.current} type="password" autoComplete="current-password" onChange={event => setPasswords(current => ({ ...current, current: event.target.value }))} /></label>
              <label>New password<input value={passwords.next} type="password" minLength={8} autoComplete="new-password" onChange={event => setPasswords(current => ({ ...current, next: event.target.value }))} /></label>
              <label>Confirm new password<input value={passwords.confirm} type="password" minLength={8} autoComplete="new-password" onChange={event => setPasswords(current => ({ ...current, confirm: event.target.value }))} /></label>
            </div>
            <p className={styles.fieldNote}>Use at least 8 characters. Aura never displays or returns your password.</p>
            {passwordError && <p className={styles.error} role="alert">{passwordError}</p>}
            {passwordMessage && <p className={styles.success} role="status">{passwordMessage}</p>}
            <div className={styles.actions}><button type="submit" className="primary-btn" disabled={passwordPending}>{passwordPending ? 'Changing…' : 'Change password'}</button></div>
          </form>
        </Card>
      </div>
    </div>
  );
}
