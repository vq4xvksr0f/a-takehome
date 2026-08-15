'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import type { LeadState } from '@/lib/api';

interface Props {
  leadId: string;
  initialState: LeadState;
}

/**
 * One-way state transition control: PENDING → REACHED_OUT.
 * PATCHes the lead through the same-origin proxy; the JWT cookie is attached
 * automatically by the browser. Hidden/disabled once the lead is REACHED_OUT.
 */
export default function MarkReachedOutButton({ leadId, initialState }: Props) {
  const router = useRouter();
  const [state, setState] = useState<LeadState>(initialState);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');

  if (state === 'REACHED_OUT') {
    return <span className="badge badge-reached-out">Reached out</span>;
  }

  async function markReachedOut() {
    setPending(true);
    setError('');
    try {
      const res = await fetch(`/api/leads/${leadId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state: 'REACHED_OUT' }),
      });

      if (res.ok) {
        setState('REACHED_OUT');
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
      // If the backend says the transition is illegal (409), the lead is
      // likely already REACHED_OUT — sync the UI from the server.
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
        className="btn btn-primary"
        onClick={markReachedOut}
        disabled={pending}
      >
        {pending ? 'Updating…' : 'Mark as reached out'}
      </button>
      {error && <span className="inline-error">{error}</span>}
    </span>
  );
}
