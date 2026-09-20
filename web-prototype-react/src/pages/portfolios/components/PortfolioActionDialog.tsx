import { useEffect, useRef, type FormEvent } from 'react';
import { createPortal } from 'react-dom';
import { FormErrorSummary } from '../../../components/ui/ApiErrorState';
import styles from '../PortfolioIntegration.module.css';

export type PortfolioAction = 'rename' | 'duplicate' | 'delete';

type PortfolioActionDialogProps = {
  action: PortfolioAction;
  portfolioName: string;
  value: string;
  busy: boolean;
  error: unknown;
  onValueChange: (value: string) => void;
  onCancel: () => void;
  onSubmit: () => void;
};

const actionCopy = {
  rename: {
    title: 'Rename portfolio',
    submitTitle: 'Save',
    description: 'Choose a clear name for this portfolio.',
  },
  duplicate: {
    title: 'Duplicate portfolio',
    submitTitle: 'Duplicate',
    description: 'Create a separate copy with the same saved holdings.',
  },
  delete: {
    title: 'Delete portfolio',
    submitTitle: 'Delete Portfolio',
    description: 'This action permanently removes the portfolio and cannot be undone.',
  },
} as const;

export function PortfolioActionDialog({
  action,
  portfolioName,
  value,
  busy,
  error,
  onValueChange,
  onCancel,
  onSubmit,
}: PortfolioActionDialogProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const dialogRef = useRef<HTMLElement>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const busyRef = useRef(busy);
  const onCancelRef = useRef(onCancel);
  const copy = actionCopy[action];
  const titleId = `portfolio-${action}-dialog-title`;
  const descriptionId = `portfolio-${action}-dialog-description`;
  const isDelete = action === 'delete';
  busyRef.current = busy;
  onCancelRef.current = onCancel;

  useEffect(() => {
    returnFocusRef.current = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    (isDelete ? closeButtonRef.current : inputRef.current)?.focus();

    const handleDialogKeys = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !busyRef.current) {
        onCancelRef.current();
        return;
      }
      if (event.key !== 'Tab') return;
      const focusable = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>(
        'button:not(:disabled), input:not(:disabled)',
      ) ?? []);
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
    window.addEventListener('keydown', handleDialogKeys);
    return () => {
      window.removeEventListener('keydown', handleDialogKeys);
      document.body.style.overflow = previousOverflow;
      returnFocusRef.current?.focus();
    };
  }, [isDelete]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!busy && (isDelete || value.trim())) onSubmit();
  }

  return createPortal(
    <div className={styles.actionDialogOverlay}>
      <button
        type="button"
        className={styles.actionDialogBackdrop}
        aria-label={`Close ${copy.title.toLowerCase()}`}
        disabled={busy}
        onClick={onCancel}
      />
      <section
        ref={dialogRef}
        className={`${styles.actionDialog} ${isDelete ? styles.actionDialogDanger : ''}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
      >
        <header className={styles.actionDialogHeader}>
          <div>
            <h2 id={titleId}>{copy.title}</h2>
            <p id={descriptionId}>{copy.description}</p>
          </div>
          <button
            ref={closeButtonRef}
            type="button"
            className={styles.actionDialogClose}
            aria-label={`Close ${copy.title.toLowerCase()}`}
            disabled={busy}
            onClick={onCancel}
          >×</button>
        </header>

        <form onSubmit={submit}>
          {isDelete ? (
            <div className={styles.deleteConfirmation} role="note">
              <strong>{portfolioName}</strong>
              <span>All saved holdings and this portfolio record will be removed.</span>
            </div>
          ) : (
            <label className={styles.actionDialogField}>
              <span>Portfolio name</span>
              <input
                ref={inputRef}
                autoComplete="off"
                value={value}
                disabled={busy}
                onChange={event => onValueChange(event.target.value)}
                placeholder="Portfolio name"
                required
              />
            </label>
          )}

          {Boolean(error) && (
            <div className={styles.actionDialogError}>
              <FormErrorSummary error={error} />
            </div>
          )}

          <div className={styles.actionDialogActions}>
            <button type="button" className="secondary-btn" onClick={onCancel} disabled={busy}>Cancel</button>
            <button
              type="submit"
              className={isDelete ? styles.deleteConfirmButton : 'primary-btn'}
              disabled={busy || (!isDelete && !value.trim())}
            >
              {busy ? 'Working…' : copy.submitTitle}
            </button>
          </div>
        </form>
      </section>
    </div>,
    document.body,
  );
}
