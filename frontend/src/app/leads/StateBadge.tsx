import type { LeadState } from '@/types/lead';

/** Shared PENDING / REACHED_OUT pill, used by the board card and detail page. */
export default function StateBadge({ state }: { state: LeadState }) {
  const reachedOut = state === 'REACHED_OUT';
  return (
    <span className={`badge ${reachedOut ? 'badge-reached-out' : 'badge-pending'}`}>
      {reachedOut ? 'Reached out' : 'Pending'}
    </span>
  );
}
