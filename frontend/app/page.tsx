'use client';

import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';

const ACCEPTED_RESUME_TYPES = '.pdf,.doc,.docx';

interface FieldErrors {
  firstName?: string;
  lastName?: string;
  email?: string;
  resume?: string;
}

/**
 * Map backend 422 field-level errors onto our form fields where possible.
 * The backend's error envelope is {detail, code}; FastAPI's default 422 body
 * uses {detail: [{loc: [...], msg: ...}]}, so handle both shapes defensively.
 */
function mapValidationErrors(body: unknown): FieldErrors {
  const errors: FieldErrors = {};
  if (typeof body !== 'object' || body === null) return errors;
  const detail = (body as { detail?: unknown }).detail;
  if (!Array.isArray(detail)) return errors;

  for (const item of detail) {
    if (typeof item !== 'object' || item === null) continue;
    const loc = (item as { loc?: unknown }).loc;
    const msg = (item as { msg?: unknown }).msg;
    if (!Array.isArray(loc) || typeof msg !== 'string') continue;
    const field = String(loc[loc.length - 1]);
    const cleanMsg = msg.replace(/^Value error, /i, '');
    if (field === 'first_name') errors.firstName = cleanMsg;
    else if (field === 'last_name') errors.lastName = cleanMsg;
    else if (field === 'email') errors.email = cleanMsg;
    else if (field === 'resume' || field === 'file') errors.resume = cleanMsg;
  }
  return errors;
}

export default function LeadFormPage() {
  const router = useRouter();
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [resume, setResume] = useState<File | null>(null);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  function validate(): FieldErrors {
    const errors: FieldErrors = {};
    if (!firstName.trim()) errors.firstName = 'First name is required.';
    if (!lastName.trim()) errors.lastName = 'Last name is required.';
    if (!email.trim()) {
      errors.email = 'Email is required.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      errors.email = 'Enter a valid email address.';
    }
    if (!resume) errors.resume = 'Please attach your resume (.pdf, .doc, or .docx).';
    return errors;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError('');

    const errors = validate();
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setSubmitting(true);
    try {
      const formData = new FormData();
      formData.append('first_name', firstName.trim());
      formData.append('last_name', lastName.trim());
      formData.append('email', email.trim());
      if (resume) formData.append('resume', resume);

      // Same-origin call; next.config.js rewrites() proxies /api/* to the
      // backend. Do NOT set Content-Type manually — the browser must set the
      // multipart boundary.
      const res = await fetch('/api/leads', {
        method: 'POST',
        body: formData,
      });

      if (res.status === 201) {
        router.push('/success');
        return;
      }

      let body: unknown = null;
      try {
        body = await res.json();
      } catch {
        // Non-JSON error body — handled by fallback below.
      }

      if (res.status === 422) {
        const mapped = mapValidationErrors(body);
        if (Object.keys(mapped).length > 0) {
          setFieldErrors(mapped);
        } else {
          setFormError('Please check the form and try again.');
        }
        return;
      }

      const detail =
        typeof body === 'object' && body !== null
          ? (body as { detail?: unknown }).detail
          : null;
      setFormError(
        typeof detail === 'string'
          ? detail
          : 'Something went wrong submitting your information. Please try again.'
      );
    } catch {
      setFormError('Network error — please check your connection and try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="centered-page">
      <div className="card form-card">
        <h1 className="page-title">Start your case evaluation</h1>
        <p className="page-subtitle">
          Tell us how to reach you and attach your resume. An attorney will
          review your submission and get back to you.
        </p>

        <form onSubmit={handleSubmit} noValidate>
          <div className="field-row">
            <div className="field">
              <label htmlFor="firstName">First name</label>
              <input
                id="firstName"
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                autoComplete="given-name"
                aria-invalid={Boolean(fieldErrors.firstName)}
              />
              {fieldErrors.firstName && (
                <p className="field-error">{fieldErrors.firstName}</p>
              )}
            </div>
            <div className="field">
              <label htmlFor="lastName">Last name</label>
              <input
                id="lastName"
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                autoComplete="family-name"
                aria-invalid={Boolean(fieldErrors.lastName)}
              />
              {fieldErrors.lastName && (
                <p className="field-error">{fieldErrors.lastName}</p>
              )}
            </div>
          </div>

          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              aria-invalid={Boolean(fieldErrors.email)}
            />
            {fieldErrors.email && <p className="field-error">{fieldErrors.email}</p>}
          </div>

          <div className="field">
            <label htmlFor="resume">Resume</label>
            <input
              id="resume"
              type="file"
              accept={ACCEPTED_RESUME_TYPES}
              onChange={(e) => setResume(e.target.files?.[0] ?? null)}
              aria-invalid={Boolean(fieldErrors.resume)}
            />
            <p className="field-hint">Accepted formats: PDF, DOC, DOCX (max 10 MB).</p>
            {fieldErrors.resume && <p className="field-error">{fieldErrors.resume}</p>}
          </div>

          {formError && (
            <div className="alert alert-error" role="alert">
              {formError}
            </div>
          )}

          <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
            {submitting ? 'Submitting…' : 'Submit'}
          </button>
        </form>
      </div>
    </main>
  );
}
