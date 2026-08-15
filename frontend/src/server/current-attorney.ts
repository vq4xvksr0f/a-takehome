import 'server-only';
import { cookies } from 'next/headers';

/**
 * Read the signed-in attorney's email from the `alma_token` JWT for display.
 *
 * This decodes the payload WITHOUT verifying the signature — it is only for
 * rendering "who is logged in" in the UI. Real authentication is enforced by
 * middleware (presence) and the backend (signature + expiry on every call),
 * so a tampered display value here is cosmetic only and never grants access.
 */
export function getCurrentAttorneyEmail(): string | null {
  const token = cookies().get('alma_token')?.value;
  if (!token) return null;

  const parts = token.split('.');
  if (parts.length !== 3) return null;

  try {
    // JWT payloads are base64url-encoded JSON.
    const payload = JSON.parse(
      Buffer.from(parts[1], 'base64url').toString('utf-8')
    ) as { email?: unknown };
    return typeof payload.email === 'string' ? payload.email : null;
  } catch {
    return null;
  }
}
