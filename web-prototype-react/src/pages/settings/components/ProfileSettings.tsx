import type { Dispatch, SetStateAction } from 'react';
import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';
import type { UserSettings } from '../../../types/settings';

interface ProfileSettingsProps {
  form: UserSettings;
  savedSettings: UserSettings;
  initials: string;
  onFormChange: Dispatch<SetStateAction<UserSettings>>;
  onSave: () => void;
}

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
          <label>
            <span>Language</span>
            <small>Interface language preference</small>
            <span className="settings-field settings-select-field">
              <Icon name="reports" size={16} />
              <select
                value={form.language}
                onChange={event => onFormChange({ ...form, language: event.target.value })}
              >
                <option>English</option>
                <option>Thai</option>
              </select>
              <Icon name="chevron-down" size={14} />
            </span>
          </label>
          <label className="timezone-field">
            <span>Timezone</span>
            <small>Used for dates and report timestamps</small>
            <span className="settings-field settings-select-field">
              <Icon name="calendar" size={16} />
              <select
                value={form.timezone}
                onChange={event => onFormChange({ ...form, timezone: event.target.value })}
              >
                <option>UTC+06:30 Yangon</option>
                <option>UTC+07:00 Bangkok</option>
              </select>
              <Icon name="chevron-down" size={14} />
            </span>
          </label>
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
