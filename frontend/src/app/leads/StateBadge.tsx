import type { LeadState } from '@/types/lead';
import styles from './StateBadge.module.css';

/** Shared PENDING / REACHED_OUT pill, used by the board card and detail page. */
export default function StateBadge({ state }: { state: LeadState }) {
  const reachedOut = state === 'REACHED_OUT';
  return (
    <span className={`${styles.badge} ${reachedOut ? styles['badge-reached-out'] : styles['badge-pending']}`}>
      {reachedOut ? 'Reached out' : 'Pending'}
    </span>
  );
}
