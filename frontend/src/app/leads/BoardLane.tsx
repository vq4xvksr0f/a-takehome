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

  return (
    <section
      ref={setNodeRef}
      className={`${boardStyles['board-lane']} ${laneClass}${highlighted ? ` ${boardStyles.boardLaneOver}` : ''}`}
      aria-label={title}
    >
      <header className={boardStyles['board-lane-header']}>
        <h2 className={boardStyles['board-lane-title']}>{title}</h2>
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
