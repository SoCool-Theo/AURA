import { useState } from 'react';
import type { FormEvent } from 'react';
import { AuthField } from './AuthField';
import { AuthLayout } from './AuthLayout';
import styles from './AuthPage.module.css';

interface LoginErrors {
  email?: string;
  password?: string;
}

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [errors, setErrors] = useState<LoginErrors>({});

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const nextErrors: LoginErrors = {};
    if (!email.trim()) {
      nextErrors.email = 'Enter your email address.';
    } else if (!/^\S+@\S+\.\S+$/.test(email)) {
      nextErrors.email = 'Enter a valid email address.';
    }
    if (!password) {
      nextErrors.password = 'Enter your password.';
    }

    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;

    alert('The login interface is ready. Backend authentication will be connected in a later phase.');
  }

  function showPrototypeNotice(action: string) {
    alert(`${action} will be connected when Aura authentication services are implemented.`);
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
            if (errors.password) setErrors(current => ({ ...current, password: undefined }));
          }}
        />

        <button
          type="button"
          className={styles.forgotPassword}
          onClick={() => showPrototypeNotice('Password recovery')}
        >
          Forgot password?
        </button>

        <button type="submit" className={styles.submitButton}>Sign In</button>
      </form>

      <div className={styles.authDivider}><span>or continue with</span></div>

      <div className={styles.socialButtons}>
        <button type="button" onClick={() => showPrototypeNotice('Google sign-in')}>
          <svg className={styles.googleMark} viewBox="0 0 24 24" aria-hidden="true">
            <path fill="#4285F4" d="M21.6 12.23c0-.71-.06-1.39-.18-2.05H12v3.87h5.38a4.6 4.6 0 0 1-1.99 3.02v2.51h3.23c1.89-1.74 2.98-4.31 2.98-7.35Z" />
            <path fill="#34A853" d="M12 22c2.7 0 4.96-.9 6.62-2.42l-3.23-2.51c-.9.6-2.04.95-3.39.95-2.61 0-4.81-1.76-5.6-4.12H3.06v2.59A10 10 0 0 0 12 22Z" />
            <path fill="#FBBC05" d="M6.4 13.9A6.01 6.01 0 0 1 6.09 12c0-.66.11-1.3.31-1.9V7.51H3.06A10 10 0 0 0 2 12c0 1.61.39 3.14 1.06 4.49L6.4 13.9Z" />
            <path fill="#EA4335" d="M12 5.98c1.47 0 2.79.5 3.82 1.49l2.87-2.87C16.96 2.99 14.7 2 12 2a10 10 0 0 0-8.94 5.51L6.4 10.1c.79-2.36 2.99-4.12 5.6-4.12Z" />
          </svg>
          Google
        </button>
        <button type="button" onClick={() => showPrototypeNotice('Apple sign-in')}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M16.7 12.8c0-2.5 2-3.7 2.1-3.8a4.5 4.5 0 0 0-3.5-1.9c-1.5-.2-2.9.9-3.7.9-.8 0-2-1-3.3-.9a4.8 4.8 0 0 0-4 2.4c-1.7 3-.4 7.3 1.2 9.7.8 1.2 1.8 2.5 3.1 2.4 1.2 0 1.7-.8 3.3-.8 1.5 0 2 .8 3.3.8 1.4 0 2.2-1.2 3-2.4a10.5 10.5 0 0 0 1.4-2.9 4.2 4.2 0 0 1-2.9-3.5ZM14.3 5.5a4.2 4.2 0 0 0 1-3c-1.1 0-2.4.7-3.1 1.5a4 4 0 0 0-1 2.9c1.2.1 2.3-.6 3.1-1.4Z" />
          </svg>
          Apple
        </button>
      </div>

      <p className={styles.authSwitch}>
        Don’t have an account?{' '}
        <button type="button" onClick={() => showPrototypeNotice('Account registration')}>Sign up</button>
      </p>
    </AuthLayout>
  );
}
