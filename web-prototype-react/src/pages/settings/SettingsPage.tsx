import { useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import type { UserSettings } from '../../types/settings';
import { ProfileSettings } from './components/ProfileSettings';
import { SettingsNavigation } from './components/SettingsNavigation';
import type { SettingsSection } from './components/SettingsNavigation';
import { SettingsPlaceholder } from './components/SettingsPlaceholder';

interface SettingsPageProps {
  settings: UserSettings;
  setSettings: Dispatch<SetStateAction<UserSettings>>;
}

const SECTIONS: SettingsSection[] = [
  { name: 'Profile', icon: 'assistant', description: 'Personal details' },
  { name: 'Preferences', icon: 'analytics', description: 'Language and region' },
  { name: 'Notifications', icon: 'bell', description: 'Updates and alerts' },
  { name: 'Security', icon: 'shield', description: 'Account protection' },
  { name: 'Billing', icon: 'reports', description: 'Plan and invoices' },
];

export function SettingsPage({ settings, setSettings }: SettingsPageProps) {
  const [form, setForm] = useState(settings);
  const [tab, setTab] = useState('Profile');
  const initials = form.name
    .split(/\s+/)
    .filter(Boolean)
    .map(part => part[0])
    .slice(0, 2)
    .join('')
    .toUpperCase() || 'YL';
  const activeSection = SECTIONS.find(section => section.name === tab);

  function save() {
    setSettings(form);
    alert('Settings saved.');
  }

  return (
    <div className="page settings-page">
      <header className="settings-header">
        <div>
          <span>ACCOUNT CENTER</span>
          <h1>Settings</h1>
          <p>Manage your Aura profile, preferences, and account configuration.</p>
        </div>
        <div className="settings-saved-status">
          <i />
          <span><strong>Local profile</strong><small>Saved in this browser</small></span>
        </div>
      </header>

      <div className="settings-layout">
        <SettingsNavigation
          settings={form}
          initials={initials}
          sections={SECTIONS}
          activeTab={tab}
          onSelect={setTab}
        />

        <div className="settings-content">
          {tab === 'Profile' ? (
            <ProfileSettings
              form={form}
              savedSettings={settings}
              initials={initials}
              onFormChange={setForm}
              onSave={save}
            />
          ) : (
            <SettingsPlaceholder section={activeSection} />
          )}
        </div>
      </div>
    </div>
  );
}
