'use client';

import { useDroppable } from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import type { LeadState, LeadSummary } from '@/types/lead';
import LeadCard from './LeadCard';

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

  return (
    <section
      ref={setNodeRef}
      className={`board-lane board-lane-${state.toLowerCase()}${highlighted ? ' board-lane-over' : ''}`}
      aria-label={title}
    >
      <header className="board-lane-header">
        <h2 className="board-lane-title">{title}</h2>
        <span className="lane-count">{leads.length}</span>
      </header>

      <SortableContext items={leads.map((l) => l.id)} strategy={verticalListSortingStrategy}>
        <div className="board-lane-cards">
          {leads.length === 0 ? (
            <p className="board-lane-empty">No leads</p>
          ) : (
            leads.map((lead) => <LeadCard key={lead.id} lead={lead} />)
          )}
        </div>
      </SortableContext>
    </section>
  );
}
