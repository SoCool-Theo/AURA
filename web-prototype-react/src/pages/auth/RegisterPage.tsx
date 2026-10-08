import { useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError } from '../../api/apiClient';
import { go } from '../../app/routes';
import { useAuth } from '../../auth/useAuth';
import { AuthField } from './AuthField';
import { AuthLayout } from './AuthLayout';
import styles from './AuthPage.module.css';

interface RegisterErrors {
  email?: string;
  password?: string;
  confirmPassword?: string;
}

function getPasswordStrength(password: string) {
  if (!password) return { score: 0, label: 'Weak' };

  let score = 1;
  if (password.length >= 8) score += 1;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score += 1;
  if (/\d/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password) || password.length >= 12) score += 1;

  const labels = ['Weak', 'Weak', 'Fair', 'Good', 'Strong', 'Strong'];
  return { score, label: labels[score] };
}

export function RegisterPage() {
  const { register } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [confirmPasswordVisible, setConfirmPasswordVisible] = useState(false);
  const [errors, setErrors] = useState<RegisterErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [registrationComplete, setRegistrationComplete] = useState(false);
  const passwordStrength = getPasswordStrength(password);

  function clearError(field: keyof RegisterErrors) {
    if (errors[field]) setErrors(current => ({ ...current, [field]: undefined }));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting) return;

    const nextErrors: RegisterErrors = {};
    if (!email.trim()) {
      nextErrors.email = 'Enter your email address.';
    } else if (!/^\S+@\S+\.\S+$/.test(email)) {
      nextErrors.email = 'Enter a valid email address.';
    }
    if (password.length < 8) nextErrors.password = 'Use at least 8 characters.';
    if (!confirmPassword) {
      nextErrors.confirmPassword = 'Confirm your password.';
    } else if (confirmPassword !== password) {
      nextErrors.confirmPassword = 'Passwords do not match.';
    }
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;

    setFormError(null);
    setIsSubmitting(true);
    try {
      await register({ email: email.trim(), password });
      setPassword('');
      setConfirmPassword('');
      setRegistrationComplete(true);
    } catch (error) {
      setFormError(
        error instanceof ApiError
          ? error.message
          : 'Aura could not create the account. Please try again.',
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  if (registrationComplete) {
    return (
      <AuthLayout>
        <div className={`${styles.authHeading} ${styles.registrationComplete}`} role="status">
          <h1>Account created</h1>
          <p>Your Aura account is ready. Sign in with your email and password to continue.</p>
          <button type="button" className={styles.submitButton} onClick={() => go('login')}>
            Continue to sign in
          </button>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout>
      <div className={`${styles.authHeading} ${styles.registerHeading}`}>
        <h1>Create your account</h1>
        <p>Start your journey to smarter portfolio decisions</p>
      </div>

      <form className={`${styles.authForm} ${styles.registerForm}`} onSubmit={submit} noValidate>
        <AuthField
          id="register-email"
          label="Email address"
          type="email"
          value={email}
          placeholder="you@example.com"
          autoComplete="email"
          icon="email"
          error={errors.email}
          onChange={value => {
            setEmail(value);
            setFormError(null);
            clearError('email');
          }}
        />

        <div className={styles.passwordGroup}>
          <AuthField
            id="register-password"
            label="Password"
            type={passwordVisible ? 'text' : 'password'}
            value={password}
            placeholder="Create a strong password"
            autoComplete="new-password"
            icon="password"
            error={errors.password}
            passwordVisible={passwordVisible}
            onToggleVisibility={() => setPasswordVisible(visible => !visible)}
            onChange={value => {
              setPassword(value);
              setFormError(null);
              clearError('password');
              if (errors.confirmPassword) clearError('confirmPassword');
            }}
          />
          <div className={styles.passwordStrength} data-strength={passwordStrength.score}>
            <div aria-hidden="true">
              {Array.from({ length: 5 }, (_, index) => <i key={index} className={index < passwordStrength.score ? styles.active : ''} />)}
            </div>
            <p>Password strength: <strong>{passwordStrength.label}</strong></p>
          </div>
        </div>

        <AuthField
          id="register-confirm-password"
          label="Confirm password"
          type={confirmPasswordVisible ? 'text' : 'password'}
          value={confirmPassword}
          placeholder="Confirm your password"
          autoComplete="new-password"
          icon="password"
          error={errors.confirmPassword}
          passwordVisible={confirmPasswordVisible}
          onToggleVisibility={() => setConfirmPasswordVisible(visible => !visible)}
          onChange={value => {
            setConfirmPassword(value);
            setFormError(null);
            clearError('confirmPassword');
          }}
        />

        {formError && <p className={styles.formError} role="alert">{formError}</p>}

        <button type="submit" className={styles.submitButton} disabled={isSubmitting}>
          {isSubmitting ? 'Creating account…' : 'Create Account'}
        </button>
      </form>

      <p className={`${styles.authSwitch} ${styles.registerSwitch}`}>
        Already have an account?{' '}
        <button type="button" onClick={() => go('login')}>Sign in</button>
      </p>
    </AuthLayout>
  );
}
