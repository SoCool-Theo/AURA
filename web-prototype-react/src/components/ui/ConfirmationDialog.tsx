import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { FormErrorSummary } from './ApiErrorState';
import { Icon } from './Icon';
import styles from './ConfirmationDialog.module.css';

type ConfirmationDialogProps = {
  title: string;
  description: string;
  subject: string;
  subjectLabel: string;
  confirmLabel: string;
  busy: boolean;
  tone?: 'danger';
  iconName?: 'trash' | 'logout';
  error?: unknown;
  children?: ReactNode;
  confirmDisabled?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

export function ConfirmationDialog({
  title,
  description,
  subject,
  subjectLabel,
  confirmLabel,
  busy,
  tone,
  iconName = 'trash',
  error,
  children,
  confirmDisabled = false,
  onCancel,
  onConfirm,
}: ConfirmationDialogProps) {
  const dialogRef = useRef<HTMLElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const busyRef = useRef(busy);
  const onCancelRef = useRef(onCancel);
  busyRef.current = busy;
  onCancelRef.current = onCancel;

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    cancelRef.current?.focus();
    const handleKeys = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !busyRef.current) {
        onCancelRef.current();
        return;
      }
      if (event.key !== 'Tab') return;
      const focusable = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled)') ?? []);
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener('keydown', handleKeys);
    return () => {
      window.removeEventListener('keydown', handleKeys);
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  return createPortal(
    <div className={styles.overlay}>
      <button type="button" className={styles.backdrop} aria-label={`Close ${title.toLowerCase()}`} disabled={busy} onClick={onCancel} />
      <section ref={dialogRef} className={`${styles.dialog} ${tone === 'danger' ? styles.dangerTheme : ''}`} role="dialog" aria-modal="true" aria-labelledby="confirmation-dialog-title" aria-describedby="confirmation-dialog-description">
        <div className={styles.accent} />
        <div className={styles.content}>
          <header className={styles.header}>
            <div className={styles.titleRow}><span className={styles.icon}><Icon name={iconName} size={20} /></span><div><h2 id="confirmation-dialog-title">{title}</h2><p id="confirmation-dialog-description">{description}</p></div></div>
            <button type="button" className={styles.close} aria-label={`Close ${title.toLowerCase()}`} disabled={busy} onClick={onCancel}><Icon name="close" size={18} /></button>
          </header>
          <div className={styles.subject}><small>{subjectLabel}</small><strong>{subject}</strong></div>
          {children}
          {Boolean(error) && <div className={styles.error}><FormErrorSummary error={error} /></div>}
          <div className={styles.actions}>
            <button ref={cancelRef} type="button" className={`secondary-btn ${styles.cancel}`} disabled={busy} onClick={onCancel}>Cancel</button>
            <button type="button" className={styles.danger} disabled={busy || confirmDisabled} onClick={onConfirm}>{busy ? 'Working…' : confirmLabel}</button>
          </div>
        </div>
      </section>
    </div>,
    document.body,
  );
}
