'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import styles from './AccountMenu.module.css';

interface Props {
  email: string;
}

/**
 * Avatar button that toggles a small account menu: shows the signed-in
 * attorney's email and a Sign out action. Closes on outside click / Escape.
 */
export default function AccountMenu({ email }: Props) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const initial = email.charAt(0).toUpperCase();

  useEffect(() => {
    if (!open) return;

    function onPointerDown(e: PointerEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  async function handleLogout() {
    setPending(true);
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
    } catch {
      // Even if the request fails, go to /login — middleware bounces back if
      // the cookie somehow survived.
    } finally {
      router.push('/login');
      router.refresh();
    }
  }

  return (
    <div className={styles['account-menu']} ref={rootRef}>
      <button
        type="button"
        className={styles['account-avatar-btn']}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Account menu"
        onClick={() => setOpen((v) => !v)}
      >
        <span className={styles['attorney-avatar']} aria-hidden="true">
          {initial}
        </span>
      </button>

      {open && (
        <div className={styles['account-dropdown']} role="menu">
          <div className={styles['account-email']} title={email}>
            {email}
          </div>
          <button
            type="button"
            role="menuitem"
            className={styles['account-logout']}
            onClick={handleLogout}
            disabled={pending}
          >
            {pending ? 'Signing out…' : 'Sign out'}
          </button>
        </div>
      )}
    </div>
  );
}
