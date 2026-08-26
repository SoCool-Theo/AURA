import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';
import type { UserSettings } from '../../../types/settings';

export interface SettingsSection {
  name: string;
  icon: string;
  description: string;
}

interface SettingsNavigationProps {
  settings: UserSettings;
  initials: string;
  sections: SettingsSection[];
  activeTab: string;
  onSelect: (tab: string) => void;
}

export function SettingsNavigation({
  settings,
  initials,
  sections,
  activeTab,
  onSelect,
}: SettingsNavigationProps) {
  return (
    <Card className="settings-navigation">
      <div className="settings-nav-profile">
        <div className="settings-nav-avatar">{initials}</div>
        <div><strong>{settings.name}</strong><small>{settings.email}</small></div>
      </div>
      <nav aria-label="Settings sections">
        {sections.map(section => (
          <button
            key={section.name}
            aria-current={activeTab === section.name ? 'page' : undefined}
            className={activeTab === section.name ? 'active' : ''}
            onClick={() => onSelect(section.name)}
          >
            <span><Icon name={section.icon} size={17} /></span>
            <span><strong>{section.name}</strong><small>{section.description}</small></span>
            <i>›</i>
          </button>
        ))}
      </nav>
      <div className="settings-nav-note">
        <Icon name="shield" size={17} />
        <p>Prototype profile data remains in your browser's local storage.</p>
      </div>
    </Card>
  );
}
