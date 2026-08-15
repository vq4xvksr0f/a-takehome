import { describe, expect, it } from 'vitest';
import { mapValidationErrors, validateLeadForm } from './validation';

const validFile = new File(['x'], 'resume.pdf', { type: 'application/pdf' });

describe('validateLeadForm', () => {
  it('accepts a fully valid form', () => {
    const errors = validateLeadForm({
      firstName: 'Alex',
      lastName: 'Rivera',
      email: 'alex@example.com',
      resume: validFile,
    });
    expect(errors).toEqual({});
  });

  it('flags blank names after trimming', () => {
    const errors = validateLeadForm({
      firstName: '   ',
      lastName: '',
      email: 'alex@example.com',
      resume: validFile,
    });
    expect(errors.firstName).toBeTruthy();
    expect(errors.lastName).toBeTruthy();
  });

  it.each([
    ['', 'Email is required.'],
    ['not-an-email', 'Enter a valid email address.'],
    ['missing@tld', 'Enter a valid email address.'],
    ['spaces in@address.com', 'Enter a valid email address.'],
  ])('rejects invalid email %j', (email, message) => {
    const errors = validateLeadForm({
      firstName: 'Alex',
      lastName: 'Rivera',
      email,
      resume: validFile,
    });
    expect(errors.email).toBe(message);
  });

  it('requires a resume', () => {
    const errors = validateLeadForm({
      firstName: 'Alex',
      lastName: 'Rivera',
      email: 'alex@example.com',
      resume: null,
    });
    expect(errors.resume).toBeTruthy();
  });
});

describe('mapValidationErrors', () => {
  it('maps FastAPI 422 loc/msg entries onto form fields', () => {
    const body = {
      detail: [
        { loc: ['body', 'first_name'], msg: 'Value error, too short' },
        { loc: ['body', 'email'], msg: 'Invalid email address' },
        { loc: ['body', 'resume'], msg: 'Unsupported file type' },
      ],
    };
    expect(mapValidationErrors(body)).toEqual({
      firstName: 'too short',
      email: 'Invalid email address',
      resume: 'Unsupported file type',
    });
  });

  it('treats "file" as the resume field', () => {
    const body = { detail: [{ loc: ['body', 'file'], msg: 'too large' }] };
    expect(mapValidationErrors(body)).toEqual({ resume: 'too large' });
  });

  it('returns empty for non-FastAPI shapes', () => {
    expect(mapValidationErrors(null)).toEqual({});
    expect(mapValidationErrors({ detail: 'plain string' })).toEqual({});
    expect(mapValidationErrors({ detail: [{ noLoc: true }] })).toEqual({});
  });

  it('ignores unknown field names', () => {
    const body = { detail: [{ loc: ['body', 'other'], msg: 'something' }] };
    expect(mapValidationErrors(body)).toEqual({});
  });
});
