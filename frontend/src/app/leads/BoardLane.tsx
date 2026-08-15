'use client';

import { useDroppable } from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import type { LeadState, LeadSummary } from '@/types/lead';
import LeadCard from './LeadCard';
import boardStyles from './board.module.css';

interface Props {
  state: LeadState;
  title: string;
  leads: LeadSummary[];
  /** Whether the dragged card is currently over this lane (drives highlight). */
  highlighted: boolean;
}

/**
 * One droppable swim lane. The lane body is a droppable target (for dropping
 * into an empty lane or at the end), and its cards form a SortableContext so
 * they shuffle aside to reveal the drop position while dragging.
 */
export default function BoardLane({ state, title, leads, highlighted }: Props) {
  const { setNodeRef } = useDroppable({ id: state });

  const laneClass =
    state === 'PENDING' ? boardStyles.lanePending : boardStyles.laneReachedOut;
  const iconClass =
    state === 'PENDING' ? boardStyles['lane-icon-pending'] : boardStyles['lane-icon-reached'];

  return (
    <section
      ref={setNodeRef}
      className={`${boardStyles['board-lane']} ${laneClass}${highlighted ? ` ${boardStyles.boardLaneOver}` : ''}`}
      aria-label={title}
    >
      <header className={boardStyles['board-lane-header']}>
        <h2 className={boardStyles['board-lane-title']}>
          {/* Heroicons (outline, MIT): clock for Pending, check-circle for Reached out. */}
          {state === 'PENDING' ? (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.8}
              stroke="currentColor"
              aria-hidden="true"
              className={`${boardStyles['lane-icon']} ${iconClass}`}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
              />
            </svg>
          ) : (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.8}
              stroke="currentColor"
              aria-hidden="true"
              className={`${boardStyles['lane-icon']} ${iconClass}`}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
              />
            </svg>
          )}
          {title}
        </h2>
        <span className={boardStyles['lane-count']}>{leads.length}</span>
      </header>

      <SortableContext items={leads.map((l) => l.id)} strategy={verticalListSortingStrategy}>
        <div className={boardStyles['board-lane-cards']}>
          {leads.length === 0 ? (
            <p className={boardStyles['board-lane-empty']}>No leads</p>
          ) : (
            leads.map((lead) => <LeadCard key={lead.id} lead={lead} />)
          )}
        </div>
      </SortableContext>
    </section>
  );
}
