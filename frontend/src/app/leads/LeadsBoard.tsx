'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import type { LeadSummary } from '@/types/lead';
import BoardLane from './BoardLane';
import LeadCard from './LeadCard';
import { LANES, useLeadsBoard } from './useLeadsBoard';
import boardStyles from './board.module.css';
import shared from '@/styles/shared.module.css';

const LANE_TITLES: Record<(typeof LANES)[number], string> = {
  PENDING: 'Pending',
  REACHED_OUT: 'Reached out',
};

interface Props {
  initialLeads: LeadSummary[];
}

/**
 * Two-lane leads board (Pending | Reached out). Server component passes the
 * fetched leads in; all drag/order/transition logic lives in `useLeadsBoard`.
 * The floating card while dragging is rendered in a DragOverlay so lane layout
 * stays stable while sibling cards shift to reveal the drop position.
 */
export default function LeadsBoard({ initialLeads }: Props) {
  const {
    lanes,
    error,
    activeLead,
    overLane,
    handleDragStart,
    handleDragOver,
    handleDragEnd,
    handleDragCancel,
  } = useLeadsBoard(initialLeads);

  const [query, setQuery] = useState('');

  // Client-side search over the already-loaded leads (name or email).
  // Filtering is visual only — dnd state stays keyed to the full list.
  const q = query.trim().toLowerCase();
  const filteredLanes = useMemo(() => {
    if (!q) return lanes;
    const match = (l: LeadSummary) =>
      `${l.first_name} ${l.last_name}`.toLowerCase().includes(q) ||
      l.email.toLowerCase().includes(q);
    return {
      PENDING: lanes.PENDING.filter(match),
      REACHED_OUT: lanes.REACHED_OUT.filter(match),
    } as Record<(typeof LANES)[number], LeadSummary[]>;
  }, [lanes, q]);

  const total = lanes.PENDING.length + lanes.REACHED_OUT.length;

  const sensors = useSensors(
    // Require a small movement before a drag starts so clicks still select.
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  if (total === 0) {
    return (
      <div className={boardStyles['board-empty-state']}>
        <p className={boardStyles['board-empty-title']}>No leads yet</p>
        <p className={boardStyles['board-empty-copy']}>
          Applications submitted through the{' '}
          <Link href="/" className={boardStyles['board-empty-link']}>
            public form
          </Link>{' '}
          will appear here.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className={boardStyles['board-toolbar']}>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search name or email…"
          aria-label="Search leads"
          className={boardStyles['board-search']}
        />
        <span className={boardStyles['board-total']}>
          {total} lead{total === 1 ? '' : 's'} · {lanes.PENDING.length} pending
        </span>
      </div>

      {error && (
        <div className={`${shared.alert} ${shared['alert-error']}`} role="alert">
          {error}
        </div>
      )}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
        onDragCancel={handleDragCancel}
      >
        <div className={boardStyles.board}>
          {LANES.map((state) => (
            <BoardLane
              key={state}
              state={state}
              title={LANE_TITLES[state]}
              leads={filteredLanes[state]}
              highlighted={overLane === state}
            />
          ))}
        </div>
        <DragOverlay dropAnimation={null} adjustScale={false} zIndex={1000}>
          {activeLead ? <LeadCard lead={activeLead} /> : null}
        </DragOverlay>
      </DndContext>
    </div>
  );
}
