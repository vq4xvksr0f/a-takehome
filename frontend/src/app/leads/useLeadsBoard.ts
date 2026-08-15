'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { arrayMove } from '@dnd-kit/sortable';
import type { DragEndEvent, DragOverEvent, DragStartEvent } from '@dnd-kit/core';
import type { LeadState, LeadSummary } from '@/types/lead';

export const LANES: LeadState[] = ['PENDING', 'REACHED_OUT'];

/**
 * Owns all board state and logic for the two-lane leads board.
 *
 * - `leads` is initialized from server-fetched props and kept in local state so
 *   drags apply optimistically (no waiting on the PATCH round-trip).
 * - Transitions are two-way (PENDING ↔ REACHED_OUT); a drop in the other lane
 *   PATCHes the new state, then `router.refresh()` re-syncs from the server.
 *   On failure we roll back to the pre-drag state and surface an error.
 * - Reordering within a lane is a local, visual concern (we don't persist card
 *   order — the backend has no position field). The live reorder during
 *   `onDragOver` is what shows the card dropping into the right position.
 */
export function useLeadsBoard(initialLeads: LeadSummary[]) {
  const router = useRouter();
  const [leads, setLeads] = useState<LeadSummary[]>(initialLeads);
  const [error, setError] = useState('');
  const [activeId, setActiveId] = useState<string | null>(null);
  // Lane the pointer is currently over during a drag (drives the highlight).
  const [overLane, setOverLane] = useState<LeadState | null>(null);
  // Snapshot of leads when the current drag started, for rollback.
  const [preDragLeads, setPreDragLeads] = useState<LeadSummary[]>(initialLeads);

  const lanes = useMemo(() => {
    const byState = (state: LeadState) => leads.filter((l) => l.state === state);
    return {
      PENDING: byState('PENDING'),
      REACHED_OUT: byState('REACHED_OUT'),
    } as Record<LeadState, LeadSummary[]>;
  }, [leads]);

  const activeLead = useMemo(
    () => leads.find((l) => l.id === activeId) ?? null,
    [leads, activeId]
  );

  /** Resolve a droppable id (a lane id or a card id) to its lane. */
  function resolveLane(id: string | number): LeadState | null {
    if (id === 'PENDING' || id === 'REACHED_OUT') return id;
    const lead = leads.find((l) => l.id === id);
    return lead ? lead.state : null;
  }

  function handleDragStart(event: DragStartEvent) {
    setActiveId(String(event.active.id));
    setPreDragLeads(leads);
    setError('');
  }

  /**
   * Live feedback while dragging: move the card into the hovered lane and
   * position so the user sees exactly where it will land.
   */
  function handleDragOver(event: DragOverEvent) {
    const { active, over } = event;
    if (!over) {
      setOverLane(null);
      return;
    }

    const draggedId = String(active.id);
    const overId = over.id;
    const lane = resolveLane(overId);
    setOverLane(lane);
    if (!lane) return;

    setLeads((prev) => {
      const current = prev.find((l) => l.id === draggedId);
      if (!current) return prev;
      const activeIndex = prev.findIndex((l) => l.id === draggedId);

      // Moving within the same lane → reorder to the hovered position.
      if (current.state === lane) {
        const overIndex = prev.findIndex((l) => l.id === overId);
        if (overIndex === -1 || activeIndex === overIndex) return prev;
        return arrayMove(prev, activeIndex, overIndex);
      }

      // Moving across lanes → change state, then place the card at the hovered
      // card's index (or at the end of the lane when hovering empty lane body).
      const moved: LeadSummary = { ...current, state: lane };
      const without = prev.filter((l) => l.id !== draggedId);
      const overIndex = without.findIndex((l) => l.id === overId);
      if (overIndex === -1) {
        // Hovering the lane container itself — append to that lane's end.
        return [...without, moved];
      }
      const next = [...without];
      next.splice(overIndex, 0, moved);
      return next;
    });
  }

  async function persistState(id: string, newState: LeadState) {
    try {
      const res = await fetch(`/api/leads/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state: newState }),
      });

      if (res.ok || res.status === 409) {
        // 409 = already in that state on the server; either way re-sync truth.
        router.refresh();
        return;
      }

      setLeads(preDragLeads); // roll back optimistic move
      let detail: unknown = null;
      try {
        detail = (await res.json()).detail;
      } catch {
        // fall through
      }
      setError(typeof detail === 'string' ? detail : 'Could not update the lead. Please try again.');
    } catch {
      setLeads(preDragLeads);
      setError('Network error — please try again.');
    }
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    const draggedId = String(active.id);
    const finalLead = leads.find((l) => l.id === draggedId);
    const originalLead = preDragLeads.find((l) => l.id === draggedId);
    setActiveId(null);
    setOverLane(null);

    if (!over || !finalLead || !originalLead) {
      setLeads(preDragLeads); // dropped outside — restore
      return;
    }

    // State changed across the drag → persist it (two-way).
    if (finalLead.state !== originalLead.state) {
      persistState(draggedId, finalLead.state);
    }
    // Same-lane reorder is already reflected in local state; nothing to persist.
  }

  function handleDragCancel() {
    setActiveId(null);
    setOverLane(null);
    setLeads(preDragLeads);
  }

  return {
    lanes,
    error,
    activeLead,
    overLane,
    handleDragStart,
    handleDragOver,
    handleDragEnd,
    handleDragCancel,
  };
}
