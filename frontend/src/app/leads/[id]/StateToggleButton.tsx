'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import type { LeadState } from '@/types/lead';

interface Props {
  leadId: string;
  initialState: LeadState;
}

/**
 * Two-way state control: PENDING ↔ REACHED_OUT. Reverting to PENDING is
 * allowed so an attorney can undo an accidental transition. PATCHes the lead
 * through the same-origin proxy; the JWT cookie is attached automatically.
 */
export default function StateToggleButton({ leadId, initialState }: Props) {
  const router = useRouter();
  const [state, setState] = useState<LeadState>(initialState);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');

  const target: LeadState = state === 'PENDING' ? 'REACHED_OUT' : 'PENDING';
  const label =
    state === 'PENDING' ? 'Mark as reached out' : 'Move back to pending';

  async function toggle() {
    setPending(true);
    setError('');
    try {
      const res = await fetch(`/api/leads/${leadId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state: target }),
      });

      if (res.ok) {
        setState(target);
        router.refresh(); // re-render the server component with fresh data
        return;
      }

      let detail: unknown = null;
      try {
        detail = (await res.json()).detail;
      } catch {
        // fall through
      }
      setError(
        typeof detail === 'string' ? detail : 'Could not update the lead. Please try again.'
      );
      // A 409 means we're out of sync with the server — re-sync from it.
      if (res.status === 409) router.refresh();
    } catch {
      setError('Network error — please try again.');
    } finally {
      setPending(false);
    }
  }

  return (
    <span className="state-control">
      <button
        type="button"
        className={state === 'PENDING' ? 'btn btn-primary' : 'btn btn-secondary'}
        onClick={toggle}
        disabled={pending}
      >
        {pending ? 'Updating…' : label}
      </button>
      {error && <span className="inline-error">{error}</span>}
    </span>
  );
}
