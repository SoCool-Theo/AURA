import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';
import type { SettingsSection } from './SettingsNavigation';

interface SettingsPlaceholderProps {
  section: SettingsSection | undefined;
}

export function SettingsPlaceholder({ section }: SettingsPlaceholderProps) {
  const name = section?.name || 'Settings';
  const icon = section?.icon || 'settings';

  return (
    <Card className="empty-settings">
      <div className="empty-settings-icon"><Icon name={icon} size={27} /></div>
      <span>ACCOUNT SETTINGS</span>
      <h2>{name}</h2>
      <p>
        {name} options are not available yet. This page will be updated when those account features are ready.
      </p>
      <div className="empty-settings-preview">
        <div>
          <span><Icon name={icon} size={16} /></span>
          <div><strong>{section?.description}</strong><small>Coming later</small></div>
        </div>
        <b>Coming later</b>
      </div>
      <div className="empty-settings-boundary">
        <Icon name="shield" size={16} />
        <p>No account-service functionality has been added during this design phase.</p>
      </div>
    </Card>
  );
}
