import { useRef, useState } from 'react';
import { usePortfolioPrivacy } from '../../../privacy/PortfolioPrivacy';
import { useLearnProgress } from '../../../learn/LearnProgress';
import { ConfirmationDialog } from '../../../components/ui/ConfirmationDialog';
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

// Privacy is local to this account/browser; remaining previews have no API access.
export function DeferredSettingsSections() {
  const { hideValues, ready, storageError, setHideValues, resetPrivacy } = usePortfolioPrivacy();
  const { resetLocalData } = useLearnProgress();
  const [showAbout, setShowAbout] = useState(false);
  const [showReset, setShowReset] = useState(false);
  const [resetBusy, setResetBusy] = useState(false);
  const [resetError, setResetError] = useState<string | null>(null);
  const [resetNotice, setResetNotice] = useState<string | null>(null);
  const resetAuthorized = useRef(false);
  const busyRef = useRef(false);
  function requestReset() {
    if (busyRef.current || !ready) return;
    resetAuthorized.current = true;
    setResetError(null); setResetNotice(null); setShowReset(true);
  }
  function cancelReset() {
    if (busyRef.current) return;
    resetAuthorized.current = false;
    setShowReset(false); setResetError(null);
  }
  async function confirmReset() {
    if (!resetAuthorized.current || busyRef.current) return;
    busyRef.current = true; setResetBusy(true); setResetError(null);
    try {
      await resetLocalData();
      // Reset privacy last: do not reveal values if progress cleanup fails.
      await resetPrivacy();
      resetAuthorized.current = false; setShowReset(false);
      setResetNotice('Local data reset. Learn progress is cleared and Hide portfolio values is off for this account in this browser.');
    } catch {
      setResetError('Local reset incomplete. Some local settings may already have reset. Please try again.');
    } finally { busyRef.current = false; setResetBusy(false); }
  }
  return <><div className={styles.deferredColumns}>
    {sections.map(section => <Card key={section.id} className={styles.formCard}>
      <section aria-labelledby={`${section.id}-heading`}>
        <div className={styles.sectionHeading}>
          <span className={`${styles.sectionIcon} ${styles.securityIcon}`}><Icon name={section.icon} size={19} /></span>
          <div><h2 id={`${section.id}-heading`}>{section.title}</h2><p>{section.id === 'data-support' ? 'Manage local learning data and learn about Aura.' : 'Privacy preferences for this account in this browser.'}</p></div>
        </div>
        <div className={styles.deferredItems}>
          {section.items.map(item => item.id === 'hide-values' ? <button key={item.id} type="button"
            className={`${styles.deferredRow} ${styles.availableRow}`} role="switch" aria-label={item.title}
            aria-checked={hideValues} aria-describedby="hide-values-description" disabled={!ready || resetBusy}
            onClick={() => setHideValues(!hideValues)}>
            <span className={styles.deferredIcon}><Icon name="eye" size={20} /></span>
            <span className={styles.deferredCopy}>
              <span className={styles.deferredLabel}>{item.title}</span>
              <span id="hide-values-description" className={styles.availableDescription}>Hide personal amounts and share quantities. Remembered for this account in this browser only.</span>
            </span>
            <span className={`${styles.privacySwitch} ${hideValues ? styles.privacySwitchOn : ''}`} aria-hidden="true"><i /></span>
          </button> : item.id === 'about' || item.id === 'reset-data' ? <button key={item.id} type="button"
            className={`${styles.deferredRow} ${styles.availableRow}`} aria-label={item.title}
            aria-describedby={`${item.id}-description`} aria-haspopup="dialog" disabled={item.id === 'reset-data' && (!ready || resetBusy)} onClick={() => item.id === 'about' ? setShowAbout(true) : requestReset()}>
            <span className={styles.deferredIcon}><Icon name={item.icon} size={20} /></span>
            <span className={styles.deferredCopy}>
              <span className={`${styles.deferredLabel} ${styles.availableLabel}`}>{item.title}</span>
              <span id={`${item.id}-description`} className={styles.availableDescription}>{item.description}</span>
            </span>
            <Icon name="chevron-right" size={18} />
          </button> : <div key={item.id} className={styles.deferredRow}>
            <span className={styles.deferredIcon}><Icon name={item.icon} size={20} /></span>
            <div className={styles.deferredCopy}>
              <button type="button" disabled aria-describedby={`${item.id}-description`} className={styles.deferredLabel}>{item.title}</button>
              <p id={`${item.id}-description`}>{item.description}</p>
            </div>
            <span className={styles.unavailableBadge}>Not available yet</span>
          </div>)}
        </div>
        {section.id === 'privacy-alerts' && storageError && <p className={styles.error} role="alert">{storageError}</p>}
      </section>
    </Card>)}
  </div>
    {resetNotice && <p className={styles.success} role="status">{resetNotice}</p>}
    {showAbout && <AboutAuraDialog onClose={() => setShowAbout(false)} />}
    {showReset && <ConfirmationDialog title="Reset local data?" tone="danger"
      description="This clears Learn progress and turns Hide portfolio values off for your current account in this browser. Your account, portfolios, holdings, reports, simulations, watchlist, and signed-in session stay unchanged. Other accounts’ preferences are not reset."
      subject="Learn progress and local privacy preferences" subjectLabel="THIS BROWSER ONLY"
      confirmLabel="Reset local data" busy={resetBusy} onCancel={cancelReset} onConfirm={() => void confirmReset()}>
      {resetError && <p className={styles.error} role="alert">{resetError}</p>}
    </ConfirmationDialog>}
  </>;
}
