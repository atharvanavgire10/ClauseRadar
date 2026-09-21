import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getErrorMessage } from '../api';
import { useAuth } from '../auth';
import { PageHeader } from '../components';
import { validateEmail, validatePassword } from '../validation';

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const next: Record<string, string> = {};
    const emailErr = validateEmail(email);
    const pwErr = validatePassword(password);
    if (emailErr) next.email = emailErr;
    if (pwErr) next.password = pwErr;
    setErrors(next);
    if (Object.keys(next).length > 0) return;
    setSubmitting(true);
    try {
      await register(email, password, displayName.trim() || undefined);
      navigate('/');
    } catch (err) {
      setErrors({ form: getErrorMessage(err, 'Registration failed.') });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="narrow">
      <PageHeader title="Create your workspace" subtitle="Register, then create an organization and workspace." />
      <form className="card form" onSubmit={onSubmit} noValidate>
        {errors.form && <p role="alert" className="form-error">{errors.form}</p>}
        <label className="field">
          <span>Email</span>
          <input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} aria-invalid={Boolean(errors.email)} />
          {errors.email && <em className="field-error">{errors.email}</em>}
        </label>
        <label className="field">
          <span>Display name (optional)</span>
          <input type="text" autoComplete="nickname" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
        </label>
        <label className="field">
          <span>Password (min 8 characters)</span>
          <input type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} aria-invalid={Boolean(errors.password)} />
          {errors.password && <em className="field-error">{errors.password}</em>}
        </label>
        <button className="btn" type="submit" disabled={submitting}>
          {submitting ? 'Creating account…' : 'Register'}
        </button>
        <p className="muted">Already registered? <Link to="/login">Log in</Link></p>
      </form>
    </div>
  );
}
