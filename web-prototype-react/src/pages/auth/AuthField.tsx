interface AuthFieldProps {
  id: string;
  label: string;
  type: 'email' | 'password' | 'text';
  value: string;
  placeholder: string;
  autoComplete: string;
  icon: 'email' | 'password' | 'user';
  error?: string;
  onChange: (value: string) => void;
  onToggleVisibility?: () => void;
  passwordVisible?: boolean;
}

function FieldIcon({ icon }: Pick<AuthFieldProps, 'icon'>) {
  if (icon === 'user') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="8" r="4" />
        <path d="M4.5 21a7.5 7.5 0 0 1 15 0" />
      </svg>
    );
  }

  if (icon === 'email') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <rect x="3" y="5" width="18" height="14" rx="2" />
        <path d="m4 7 8 6 8-6" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="5" y="10" width="14" height="11" rx="2" />
      <path d="M8 10V7a4 4 0 0 1 8 0v3" />
    </svg>
  );
}

function VisibilityIcon({ visible }: { visible: boolean }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      {visible ? (
        <>
          <path d="M3 3 21 21" />
          <path d="M10.6 10.7a2 2 0 0 0 2.7 2.7" />
          <path d="M9.9 4.2A10.8 10.8 0 0 1 12 4c5.4 0 9 5.5 9 5.5a15.5 15.5 0 0 1-2.2 2.7M6.2 6.2C4.2 7.6 3 9.5 3 9.5S6.6 15 12 15c1 0 2-.2 2.9-.5" />
        </>
      ) : (
        <>
          <path d="M3 12s3.6-5.5 9-5.5 9 5.5 9 5.5-3.6 5.5-9 5.5S3 12 3 12Z" />
          <circle cx="12" cy="12" r="2.5" />
        </>
      )}
    </svg>
  );
}

export function AuthField({
  id,
  label,
  type,
  value,
  placeholder,
  autoComplete,
  icon,
  error,
  onChange,
  onToggleVisibility,
  passwordVisible = false,
}: AuthFieldProps) {
  const errorId = `${id}-error`;

  return (
    <label htmlFor={id}>
      <span>{label}</span>
      <span className="auth-input-shell">
        <span className="auth-field-icon"><FieldIcon icon={icon} /></span>
        <input
          id={id}
          type={type}
          value={value}
          placeholder={placeholder}
          autoComplete={autoComplete}
          inputMode={type === 'email' ? 'email' : undefined}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? errorId : undefined}
          onChange={event => onChange(event.target.value)}
        />
        {onToggleVisibility && (
          <button
            type="button"
            className="auth-password-toggle"
            onClick={onToggleVisibility}
            aria-label={passwordVisible ? 'Hide password' : 'Show password'}
            aria-pressed={passwordVisible}
          >
            <VisibilityIcon visible={passwordVisible} />
          </button>
        )}
      </span>
      {error && <small id={errorId} className="auth-field-error">{error}</small>}
    </label>
  );
}
