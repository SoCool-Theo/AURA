import { useEffect, useRef } from 'react';
import { usePrivateText, usePrivateValue } from '../../../privacy/PortfolioPrivacy';
import styles from '../AnalyticsIntegration.module.css';

export type MetricAmountDialogContent = {
  title: string;
  percentage: string;
  amount: string;
  amountLabel: string;
  reference: string;
  explanation: string;
  tone: 'positive' | 'negative';
};

export function MetricAmountDialog({
  content,
  onClose,
}: {
  content: MetricAmountDialogContent | null;
  onClose: () => void;
}) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const privateValue = usePrivateValue();
  const privateText = usePrivateText();

  useEffect(() => {
    if (!content) return;
    closeRef.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [content, onClose]);

  if (!content) return null;

  return (
    <div className={styles.metricDialogOverlay}>
      <button
        className={styles.metricDialogBackdrop}
        type="button"
        aria-label="Close metric details"
        onClick={onClose}
      />
      <section
        className={styles.metricDialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby="metric-amount-title"
      >
        <header>
          <div>
            <small>HISTORICAL MONEY EQUIVALENT</small>
            <h2 id="metric-amount-title">{content.title}</h2>
          </div>
          <button ref={closeRef} type="button" aria-label="Close metric details" onClick={onClose}>×</button>
        </header>
        <strong className={content.tone === 'negative' ? styles.amountNegative : styles.amountPositive}>
          {privateText(content.percentage)}
        </strong>
        <span>{content.amountLabel}</span>
        <b className={content.tone === 'negative' ? styles.amountNegative : styles.amountPositive}>≈ {privateValue(content.amount)}</b>
        <div className={styles.metricDialogExplanation}>
          <strong>{privateText(content.reference)}</strong>
          <p>{privateText(content.explanation)}</p>
        </div>
        <button className="primary-btn" type="button" onClick={onClose}>Close</button>
      </section>
    </div>
  );
}
