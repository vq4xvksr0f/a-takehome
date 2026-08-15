export const ACCEPTED_RESUME_TYPES = '.pdf,.doc,.docx';
const ACCEPTED_RESUME_EXTENSIONS = new Set(['.pdf', '.doc', '.docx']);
export const MAX_RESUME_BYTES = 10 * 1024 * 1024;

export interface LeadFormValues {
  firstName: string;
  lastName: string;
  email: string;
  resume: File | null;
}

export interface FieldErrors {
  firstName?: string;
  lastName?: string;
  email?: string;
  resume?: string;
}

export function validateLeadForm(values: LeadFormValues): FieldErrors {
  const errors: FieldErrors = {};
  if (!values.firstName.trim()) errors.firstName = 'First name is required.';
  if (!values.lastName.trim()) errors.lastName = 'Last name is required.';
  if (!values.email.trim()) {
    errors.email = 'Email is required.';
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email.trim())) {
    errors.email = 'Enter a valid email address.';
  }
  if (!values.resume) {
    errors.resume = 'Please attach your resume (.pdf, .doc, or .docx).';
  } else {
    const ext = values.resume.name.slice(values.resume.name.lastIndexOf('.')).toLowerCase();
    if (!ACCEPTED_RESUME_EXTENSIONS.has(ext)) {
      errors.resume = 'Unsupported file type; allowed: .pdf, .doc, .docx';
    } else if (values.resume.size > MAX_RESUME_BYTES) {
      errors.resume = 'Resume exceeds the 10 MB limit';
    }
  }
  return errors;
}

/**
 * Map backend 422 field-level errors onto our form fields where possible.
 * The backend's error envelope is {detail, code}; FastAPI's default 422 body
 * uses {detail: [{loc: [...], msg: ...}]}, so handle both shapes defensively.
 */
export function mapValidationErrors(body: unknown): FieldErrors {
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
