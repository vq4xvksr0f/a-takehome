'use client';

import Link from 'next/link';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import type { LeadSummary } from '@/types/lead';
import { formatDate } from '@/lib/format';
import StateBadge from './StateBadge';
import styles from './LeadCard.module.css';

interface Props {
  lead: LeadSummary;
}

/**
 * A sortable, draggable card: name (links to detail), email, submitted date.
 * The sortable transform shifts sibling cards out of the way while dragging,
 * which is what shows the exact drop position. The floating card itself is
 * rendered by the board's DragOverlay.
 */
export default function LeadCard({ lead }: Props) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: lead.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`${styles['lead-card']}${isDragging ? ` ${styles['is-dragging-source']}` : ''}`}
      {...attributes}
      {...listeners}
    >
      <div className={styles['lead-card-top']}>
        <Link
          href={`/leads/${lead.id}`}
          className={`${styles['row-link']} ${styles['lead-card-name']}`}
          // Don't let the link click start a drag.
          onPointerDown={(e) => e.stopPropagation()}
        >
          {lead.first_name} {lead.last_name}
        </Link>
        <StateBadge state={lead.state} />
      </div>
      <div className={styles['lead-card-email']}>{lead.email}</div>
      <div className={styles['lead-card-date']}>Submitted {formatDate(lead.created_at)}</div>
    </div>
  );
}
