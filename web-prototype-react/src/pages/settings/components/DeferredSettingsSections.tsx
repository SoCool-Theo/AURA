import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';
import styles from '../SettingsPage.module.css';

const sections = [
  {
    id: 'privacy-alerts', title: 'Privacy & alerts', icon: 'shield',
    items: [
      { id: 'hide-values', title: 'Hide portfolio values', icon: 'eye', description: 'Hide monetary portfolio values while using Aura.' },
      { id: 'notifications', title: 'App notifications', icon: 'bell', description: 'Manage Aura notifications and alerts.' },
    ],
  },
  {
    id: 'data-support', title: 'Data & support', icon: 'server',
    items: [
      { id: 'reset-data', title: 'Reset local data', icon: 'compare', description: 'Reset browser preferences and Learn progress.' },
      { id: 'help', title: 'Help & Support', icon: 'alert', description: 'Setup and troubleshooting information.' },
      { id: 'about', title: 'About Aura', icon: 'shield', description: 'Learn about Aura and its current features.' },
    ],
  },
];

// Presentation only: these controls intentionally have no handlers or storage/API access.
export function DeferredSettingsSections() {
  return <div className={styles.deferredColumns}>
    {sections.map(section => <Card key={section.id} className={styles.formCard}>
      <section aria-labelledby={`${section.id}-heading`}>
        <div className={styles.sectionHeading}>
          <span className={`${styles.sectionIcon} ${styles.securityIcon}`}><Icon name={section.icon} size={19} /></span>
          <div><h2 id={`${section.id}-heading`}>{section.title}</h2><p>Preview only. These options are not enabled yet.</p></div>
        </div>
        <div className={styles.deferredItems}>
          {section.items.map(item => <div key={item.id} className={styles.deferredRow}>
            <span className={styles.deferredIcon}><Icon name={item.icon} size={20} /></span>
            <div className={styles.deferredCopy}>
              <button type="button" disabled aria-describedby={`${item.id}-description`} className={styles.deferredLabel}>{item.title}</button>
              <p id={`${item.id}-description`}>{item.description}</p>
            </div>
            <span className={styles.unavailableBadge}>Not available yet</span>
          </div>)}
        </div>
      </section>
    </Card>)}
  </div>;
}
