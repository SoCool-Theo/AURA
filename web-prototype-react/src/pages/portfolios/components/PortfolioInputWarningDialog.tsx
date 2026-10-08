import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Icon } from '../../../components/ui/Icon';
import type { PortfolioInputWarning } from '../portfolioInputWarning';
import { showPortfolioInputWarning } from '../portfolioInputWarning';
import styles from '../PortfolioIntegration.module.css';

export function PortfolioInputWarningDialog({
  warning,
}: {
  warning: PortfolioInputWarning | null;
}) {
  const [visible, setVisible] = useState(Boolean(warning));
  const actionRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    setVisible(Boolean(warning));
  }, [warning]);

  useEffect(() => {
    if (!visible || !warning) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    actionRef.current?.focus();
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') revealInput();
    };
    window.addEventListener('keydown', handleKey);
    return () => {
      window.removeEventListener('keydown', handleKey);
      document.body.style.overflow = previousOverflow;
    };
  }, [visible, warning]);

  function revealInput() {
    if (!warning) return;
    setVisible(false);
    showPortfolioInputWarning(warning);
  }

  if (!warning || !visible) return null;

  const titleId = 'portfolio-input-warning-title';
  const descriptionId = 'portfolio-input-warning-description';
  return createPortal(
    <div className={styles.inputWarningOverlay}>
      <div className={styles.inputWarningBackdrop} aria-hidden="true" />
      <section
        className={styles.inputWarningDialog}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
      >
        <div className={styles.inputWarningIcon} aria-hidden="true">
          <Icon name="alert" size={24} />
        </div>
        <small>INPUT NEEDS ATTENTION</small>
        <h2 id={titleId}>Check your information</h2>
        <p id={descriptionId}>{warning.message}</p>
        <button
          ref={actionRef}
          type="button"
          className="primary-btn"
          onClick={revealInput}
        >
          Show input
        </button>
      </section>
    </div>,
    document.body,
  );
}
