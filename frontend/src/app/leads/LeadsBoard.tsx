'use client';

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

  const sensors = useSensors(
    // Require a small movement before a drag starts so clicks still select.
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  return (
    <div>
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
              leads={lanes[state]}
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
