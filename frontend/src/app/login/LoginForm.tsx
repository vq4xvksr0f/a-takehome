'use client';

import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
import shared from '@/styles/shared.module.css';

export default function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setSubmitting(true);

    try {
      // Same-origin call — proxied to the backend, which responds with an
      // HttpOnly `alma_token` cookie on this origin. We never read or store
      // the token in JavaScript; the browser handles it from here on.
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), password }),
      });

      if (res.ok) {
        router.push('/leads');
        router.refresh();
        return;
      }

      if (res.status === 401) {
        // Deliberately generic — don't reveal whether the email exists.
        setError('Invalid email or password.');
        return;
      }

      let detail: unknown = null;
      try {
        detail = (await res.json()).detail;
      } catch {
        // fall through to generic message
      }
      setError(
        typeof detail === 'string' ? detail : 'Login failed. Please try again.'
      );
    } catch {
      setError('Network error — please check your connection and try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className={shared['centered-page']}>
      <div className={`${shared.card} ${shared['form-card']}`}>
        <h1 className={shared['page-title']}>Attorney sign in</h1>
        <p className={shared['page-subtitle']}>Sign in to review and manage incoming leads.</p>

        <form onSubmit={handleSubmit}>
          <div className={shared.field}>
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </div>
          <div className={shared.field}>
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          {error && (
            <div className={`${shared.alert} ${shared['alert-error']}`} role="alert">
              {error}
            </div>
          )}

          <button
            type="submit"
            className={`${shared.btn} ${shared['btn-primary']} ${shared['btn-block']}`}
            disabled={submitting}
          >
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </main>
  );
}
