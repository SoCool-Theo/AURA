import { useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError } from '../../api/apiClient';
import { go } from '../../app/routes';
import { useAuth } from '../../auth/useAuth';
import { AuthField } from './AuthField';
import { AuthLayout } from './AuthLayout';
import styles from './AuthPage.module.css';

interface LoginErrors {
  email?: string;
  password?: string;
}

export function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [errors, setErrors] = useState<LoginErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const nextErrors: LoginErrors = {};
    if (!email.trim()) {
      nextErrors.email = 'Enter your email address.';
    } else if (!/^\S+@\S+\.\S+$/.test(email)) {
      nextErrors.email = 'Enter a valid email address.';
    }
    if (!password) {
      nextErrors.password = 'Enter your password.';
    } else if (password.length < 8) {
      nextErrors.password = 'Use at least 8 characters.';
    }

    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;

    setFormError(null);
    setIsSubmitting(true);
    try {
      await login({ email: email.trim(), password });
      setPassword('');
      go('dashboard');
    } catch (error) {
      setFormError(
        error instanceof ApiError
          ? error.message
          : 'Aura could not complete sign in. Please try again.',
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthLayout>
      <div className={styles.authHeading}>
        <h1>Welcome back</h1>
        <p>Sign in to continue to your portfolio dashboard</p>
      </div>

      <form className={styles.authForm} onSubmit={submit} noValidate>
        <AuthField
          id="login-email"
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
            if (errors.email) setErrors(current => ({ ...current, email: undefined }));
          }}
        />

        <AuthField
          id="login-password"
          label="Password"
          type={passwordVisible ? 'text' : 'password'}
          value={password}
          placeholder="Enter your password"
          autoComplete="current-password"
          icon="password"
          error={errors.password}
          passwordVisible={passwordVisible}
          onToggleVisibility={() => setPasswordVisible(visible => !visible)}
          onChange={value => {
            setPassword(value);
            setFormError(null);
            if (errors.password) setErrors(current => ({ ...current, password: undefined }));
          }}
        />

        {formError && <p className={styles.formError} role="alert">{formError}</p>}

        <button type="submit" className={styles.submitButton} disabled={isSubmitting}>
          {isSubmitting ? 'Signing in…' : 'Sign In'}
        </button>
      </form>

      <p className={styles.authSwitch}>
        Don’t have an account?{' '}
        <button type="button" onClick={() => go('signup')}>Sign up</button>
      </p>
    </AuthLayout>
  );
}
