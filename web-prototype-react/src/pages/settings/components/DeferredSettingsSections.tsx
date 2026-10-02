import { useState } from 'react';
import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';
import { AboutAuraDialog } from './AboutAuraDialog';
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

// Only About Aura is enabled; the remaining previews have no storage/API access.
export function DeferredSettingsSections() {
  const [showAbout, setShowAbout] = useState(false);
  return <><div className={styles.deferredColumns}>
    {sections.map(section => <Card key={section.id} className={styles.formCard}>
      <section aria-labelledby={`${section.id}-heading`}>
        <div className={styles.sectionHeading}>
          <span className={`${styles.sectionIcon} ${styles.securityIcon}`}><Icon name={section.icon} size={19} /></span>
          <div><h2 id={`${section.id}-heading`}>{section.title}</h2><p>{section.id === 'data-support' ? 'Learn about Aura. Other options are not enabled yet.' : 'Preview only. These options are not enabled yet.'}</p></div>
        </div>
        <div className={styles.deferredItems}>
          {section.items.map(item => <div key={item.id} className={styles.deferredRow}>
            <span className={styles.deferredIcon}><Icon name={item.icon} size={20} /></span>
            <div className={styles.deferredCopy}>
              <button type="button" disabled={item.id !== 'about'} aria-describedby={`${item.id}-description`}
                className={`${styles.deferredLabel} ${item.id === 'about' ? styles.availableLabel : ''}`}
                aria-haspopup={item.id === 'about' ? 'dialog' : undefined}
                onClick={item.id === 'about' ? () => setShowAbout(true) : undefined}>{item.title}</button>
              <p id={`${item.id}-description`}>{item.description}</p>
            </div>
            {item.id === 'about' ? <Icon name="chevron-right" size={18} /> : <span className={styles.unavailableBadge}>Not available yet</span>}
          </div>)}
        </div>
      </section>
    </Card>)}
  </div>{showAbout && <AboutAuraDialog onClose={() => setShowAbout(false)} />}</>;
}
