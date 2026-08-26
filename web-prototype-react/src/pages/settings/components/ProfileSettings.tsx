import type { Dispatch, SetStateAction } from 'react';
import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';
import { AuraSelect } from '../../../components/ui/AuraSelect';
import type { AuraSelectOption } from '../../../components/ui/AuraSelect';
import type { UserSettings } from '../../../types/settings';

interface ProfileSettingsProps {
  form: UserSettings;
  savedSettings: UserSettings;
  initials: string;
  onFormChange: Dispatch<SetStateAction<UserSettings>>;
  onSave: () => void;
}

const languageOptions: ReadonlyArray<AuraSelectOption<string>> = [
  { value: 'English', label: 'English', description: 'Use Aura in English', icon: 'reports', tone: 'teal' },
  { value: 'Thai', label: 'Thai', description: 'Use Aura in Thai', icon: 'reports', tone: 'blue' },
];

const timezoneOptions: ReadonlyArray<AuraSelectOption<string>> = [
  { value: 'UTC+06:30 Yangon', label: 'UTC+06:30 Yangon', description: 'Myanmar Standard Time', icon: 'calendar', tone: 'teal' },
  { value: 'UTC+07:00 Bangkok', label: 'UTC+07:00 Bangkok', description: 'Indochina Time', icon: 'calendar', tone: 'blue' },
];

export function ProfileSettings({
  form,
  savedSettings,
  initials,
  onFormChange,
  onSave,
}: ProfileSettingsProps) {
  return (
    <>
      <Card className="settings-profile-card">
        <div className="settings-section-heading">
          <div>
            <span>PROFILE INFORMATION</span>
            <h2>Your account details</h2>
            <p>Update the information displayed throughout the Aura prototype.</p>
          </div>
          <span className="settings-profile-badge"><Icon name="assistant" size={15} /> Portfolio owner</span>
        </div>
        <div className="settings-profile-hero">
          <div className="profile-photo">{initials}<span><Icon name="spark" size={12} /></span></div>
          <div>
            <strong>{form.name}</strong>
            <small>{form.email}</small>
            <p>Your initials appear in the navigation and account menu.</p>
          </div>
          <button className="secondary-btn">Change Photo</button>
        </div>
      </Card>

      <Card className="settings-form-card">
        <div className="settings-form-heading">
          <h2>Personal Information</h2>
          <p>Keep your contact details and regional preferences up to date.</p>
        </div>
        <div className="settings-form">
          <label>
            <span>Full Name</span>
            <small>Name shown across your Aura workspace</small>
            <span className="settings-field">
              <Icon name="assistant" size={16} />
              <input
                value={form.name}
                onChange={event => onFormChange({ ...form, name: event.target.value })}
                placeholder="Enter your full name"
              />
            </span>
          </label>
          <label>
            <span>Email Address</span>
            <small>Primary account contact</small>
            <span className="settings-field">
              <span className="field-symbol">@</span>
              <input
                type="email"
                value={form.email}
                onChange={event => onFormChange({ ...form, email: event.target.value })}
                placeholder="name@example.com"
              />
            </span>
          </label>
          <label>
            <span>Phone Number</span>
            <small>Optional contact information</small>
            <span className="settings-field">
              <span className="field-symbol">＋</span>
              <input
                value={form.phone}
                onChange={event => onFormChange({ ...form, phone: event.target.value })}
                placeholder="Enter your phone number"
              />
            </span>
          </label>
          <div className="settings-form-control">
            <span>Language</span>
            <small>Interface language preference</small>
            <AuraSelect
              className="settings-field settings-aura-select"
              ariaLabel="Language"
              value={form.language}
              options={languageOptions}
              onChange={language => onFormChange({ ...form, language })}
            />
          </div>
          <div className="settings-form-control timezone-field">
            <span>Timezone</span>
            <small>Used for dates and report timestamps</small>
            <AuraSelect
              className="settings-field settings-aura-select"
              ariaLabel="Timezone"
              value={form.timezone}
              options={timezoneOptions}
              onChange={timezone => onFormChange({ ...form, timezone })}
            />
          </div>
        </div>
        <div className="settings-form-footer">
          <div><Icon name="shield" size={15} /><span>Changes are stored only in this frontend prototype.</span></div>
          <div>
            <button className="secondary-btn" onClick={() => onFormChange(savedSettings)}>Discard Changes</button>
            <button className="primary-btn settings-save" onClick={onSave}>Save Changes <span>→</span></button>
          </div>
        </div>
      </Card>
    </>
  );
}
