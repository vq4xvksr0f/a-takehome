'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

/**
 * POSTs /api/auth/logout through the same-origin proxy; the backend clears
 * the `alma_token` cookie on its response, then we head back to /login.
 */
export default function LogoutButton() {
  const router = useRouter();
  const [pending, setPending] = useState(false);

  async function handleLogout() {
    setPending(true);
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
    } catch {
      // Even if the request fails, send the user to /login — middleware will
      // bounce them back here if the cookie somehow survived.
    } finally {
      router.push('/login');
      router.refresh();
    }
  }

  return (
    <button
      type="button"
      className="btn btn-secondary"
      onClick={handleLogout}
      disabled={pending}
    >
      {pending ? 'Signing out…' : 'Sign out'}
    </button>
  );
}
