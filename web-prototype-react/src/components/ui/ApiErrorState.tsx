import { apiErrorPresentation } from '../../api/apiErrorPresentation';
import { Card } from './Card';
import { Icon } from './Icon';
import styles from './ApiErrorState.module.css';

type ErrorActions = {
  onRetry?: () => void;
  onBack?: () => void;
  retryTitle?: string;
  backTitle?: string;
};

type ErrorStateProps = ErrorActions & {
  error: unknown;
  fallbackMessage?: string;
  resourceName?: string;
  message?: string;
  stale?: boolean;
};

function ErrorContent({
  error,
  fallbackMessage,
  resourceName,
  message,
  stale,
  onRetry,
  onBack,
  retryTitle = 'Try again',
  backTitle = 'Go back',
  compact = false,
}: ErrorStateProps & { compact?: boolean }) {
  const presentation = apiErrorPresentation(error, { fallbackMessage, resourceName, message });
  return <div className={compact ? styles.compact : ''}>
    <div className={styles.heading}>
      <span className={styles.icon}><Icon name={presentation.icon} size={compact ? 19 : 24} /></span>
      <div><small className={styles.code}>{presentation.code}</small><h2 className={styles.title}>{presentation.title}</h2></div>
    </div>
    <p className={styles.message}>{presentation.message}</p>
    {stale && <small className={styles.stale}>Previously loaded information remains visible and may be out of date.</small>}
    {(onBack || (onRetry && presentation.retryable)) && <div className={styles.actions}>
      {onRetry && presentation.retryable && <button type="button" className="primary-btn" onClick={onRetry}>{retryTitle}</button>}
      {onBack && <button type="button" className="secondary-btn" onClick={onBack}>{backTitle}</button>}
    </div>}
  </div>;
}

export function ScreenErrorState(props: ErrorStateProps) {
  return <div className={styles.screen} role="alert"><Card className={styles.screenCard}><ErrorContent {...props} /></Card></div>;
}

export function InlineErrorCard(props: ErrorStateProps) {
  return <Card className={styles.inlineCard}><ErrorContent {...props} compact /></Card>;
}

export function FormErrorSummary({ error, message }: { error?: unknown; message?: string }) {
  return <InlineErrorCard error={error ?? message ?? 'Review the form and try again.'} message={message} />;
}
