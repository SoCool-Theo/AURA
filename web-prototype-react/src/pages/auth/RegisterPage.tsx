import { useState } from 'react';
import type { FormEvent } from 'react';
import { go } from '../../app/routes';
import { AuthField } from './AuthField';
import { AuthLayout } from './AuthLayout';
import styles from './AuthPage.module.css';

interface RegisterErrors {
  name?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
  terms?: string;
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
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [confirmPasswordVisible, setConfirmPasswordVisible] = useState(false);
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [errors, setErrors] = useState<RegisterErrors>({});
  const passwordStrength = getPasswordStrength(password);

  function clearError(field: keyof RegisterErrors) {
    if (errors[field]) setErrors(current => ({ ...current, [field]: undefined }));
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const nextErrors: RegisterErrors = {};
    if (name.trim().length < 2) nextErrors.name = 'Enter your full name.';
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
    if (!termsAccepted) nextErrors.terms = 'Accept the Terms of Service and Privacy Policy to continue.';

    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;

    alert('The sign-up interface is ready. Account creation will be connected when backend authentication is implemented.');
  }

  function showPolicyNotice(policy: string) {
    alert(`${policy} content will be connected when Aura account services are implemented.`);
  }

  return (
    <AuthLayout>
      <div className={`${styles.authHeading} ${styles.registerHeading}`}>
        <h1>Create your account</h1>
        <p>Start your journey to smarter portfolio decisions</p>
      </div>

      <form className={`${styles.authForm} ${styles.registerForm}`} onSubmit={submit} noValidate>
        <AuthField
          id="register-name"
          label="Full name"
          type="text"
          value={name}
          placeholder="Enter your full name"
          autoComplete="name"
          icon="user"
          error={errors.name}
          onChange={value => {
            setName(value);
            clearError('name');
          }}
        />

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
            clearError('confirmPassword');
          }}
        />

        <div className={styles.termsGroup}>
          <label className={styles.termsRow}>
            <input
              type="checkbox"
              checked={termsAccepted}
              onChange={event => {
                setTermsAccepted(event.target.checked);
                clearError('terms');
              }}
            />
            <span>
              I agree to the{' '}
              <button type="button" onClick={() => showPolicyNotice('Terms of Service')}>Terms of Service</button>
              {' '}and{' '}
              <button type="button" onClick={() => showPolicyNotice('Privacy Policy')}>Privacy Policy</button>
            </span>
          </label>
          {errors.terms && <small className={styles.termsError}>{errors.terms}</small>}
        </div>

        <button type="submit" className={styles.submitButton}>Create Account</button>
      </form>

      <p className={`${styles.authSwitch} ${styles.registerSwitch}`}>
        Already have an account?{' '}
        <button type="button" onClick={() => go('login')}>Sign in</button>
      </p>
    </AuthLayout>
  );
}
