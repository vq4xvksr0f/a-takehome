import { cookies } from 'next/headers';

/**
 * Shared types mirroring the backend API shapes.
 */

export type LeadState = 'PENDING' | 'REACHED_OUT';

export interface LeadSummary {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  state: LeadState;
  created_at: string;
}

export interface Lead extends LeadSummary {
  resume_filename: string;
  updated_at: string;
}

export interface ApiError {
  detail: string;
  code?: string;
}

/**
 * Fetch an authenticated API endpoint from a Server Component.
 *
 * Server Components run on the Next.js server, so the browser's cookies are
 * NOT attached automatically — we read the incoming request's cookies via
 * `next/headers` and forward them explicitly. The request path is `/api/...`,
 * which resolves against the Next.js server itself; the `rewrites()` proxy in
 * next.config.js forwards it to the FastAPI backend, so this goes through the
 * exact same code path as browser-originated calls.
 */
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const cookieStore = cookies();
  const cookieHeader = cookieStore
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join('; ');

  // Hit the same Next.js server on its actual bound port so the request goes
  // through the rewrites() proxy — the exact same code path and behavior as
  // browser-originated calls. PORT is read at request time (not build time),
  // so setting it at container runtime is enough.
  const port = process.env.PORT || '3000';

  return fetch(`http://127.0.0.1:${port}${path}`, {
    ...init,
    headers: {
      ...(init.headers || {}),
      cookie: cookieHeader,
    },
    // Lead data changes constantly; never serve a cached response.
    cache: 'no-store',
  });
}

/** Parse the backend's `{detail, code}` error envelope, with fallbacks. */
export async function parseApiError(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as Partial<ApiError>;
    if (typeof body.detail === 'string') return body.detail;
  } catch {
    // Non-JSON body — fall through to generic message.
  }
  return `Request failed (${res.status})`;
}
