// @vitest-environment jsdom
import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { LeadSummary } from '@/types/lead';
import { useLeadsBoard } from './useLeadsBoard';

// useRouter is only used for refresh() after a successful PATCH.
vi.mock('next/navigation', () => ({
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
}));

const lead = (id: string, state: LeadSummary['state']): LeadSummary => ({
  id,
  first_name: `First${id}`,
  last_name: `Last${id}`,
  email: `lead${id}@example.com`,
  state,
  created_at: '2026-08-15T00:00:00+00:00',
});

const initial = [lead('a', 'PENDING'), lead('b', 'PENDING'), lead('c', 'REACHED_OUT')];

/** Drive a full drag lifecycle: start → over(target) → end. */
function dragTo(
  result: { current: ReturnType<typeof useLeadsBoard> },
  activeId: string,
  overId: string
) {
  act(() => {
    result.current.handleDragStart({ active: { id: activeId } } as never);
  });
  act(() => {
    result.current.handleDragOver({ active: { id: activeId }, over: { id: overId } } as never);
  });
  act(() => {
    result.current.handleDragEnd({ active: { id: activeId }, over: { id: overId } } as never);
  });
}

describe('useLeadsBoard', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200 })));
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('groups leads into lanes by state', () => {
    const { result } = renderHook(() => useLeadsBoard(initial));
    expect(result.current.lanes.PENDING.map((l) => l.id)).toEqual(['a', 'b']);
    expect(result.current.lanes.REACHED_OUT.map((l) => l.id)).toEqual(['c']);
  });

  it('moves a card across lanes optimistically and PATCHes the new state', async () => {
    const { result } = renderHook(() => useLeadsBoard(initial));
    dragTo(result, 'a', 'REACHED_OUT');
    expect(result.current.lanes.REACHED_OUT.map((l) => l.id)).toContain('a');
    expect(result.current.lanes.PENDING.map((l) => l.id)).toEqual(['b']);
    await act(async () => {
      await vi.waitFor(() => expect(fetch).toHaveBeenCalled());
    });
    expect(fetch).toHaveBeenCalledWith(
      '/api/leads/a',
      expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ state: 'REACHED_OUT' }) })
    );
    expect(result.current.error).toBe('');
  });

  it('rolls back the optimistic move and surfaces an error when the PATCH fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        status: 500,
        json: async () => ({ detail: 'boom' }),
      }))
    );
    const { result } = renderHook(() => useLeadsBoard(initial));
    dragTo(result, 'a', 'REACHED_OUT');
    // persistState is fire-and-forget from handleDragEnd; let it settle.
    await act(async () => {
      await new Promise((r) => setTimeout(r, 0));
    });
    expect(result.current.error).toBe('boom');
    // Rolled back to pre-drag state.
    expect(result.current.lanes.PENDING.map((l) => l.id)).toEqual(['a', 'b']);
    expect(result.current.lanes.REACHED_OUT.map((l) => l.id)).toEqual(['c']);
  });

  it('dropping outside restores the pre-drag state', () => {
    const { result } = renderHook(() => useLeadsBoard(initial));
    act(() => {
      result.current.handleDragStart({ active: { id: 'a' } } as never);
    });
    act(() => {
      result.current.handleDragOver({ active: { id: 'a' }, over: { id: 'REACHED_OUT' } } as never);
    });
    // Card is visually over the other lane mid-drag...
    expect(result.current.lanes.REACHED_OUT.map((l) => l.id)).toContain('a');
    act(() => {
      result.current.handleDragEnd({ active: { id: 'a' }, over: null } as never);
    });
    // ...and restored on drop-outside.
    expect(result.current.lanes.PENDING.map((l) => l.id)).toEqual(['a', 'b']);
    expect(fetch).not.toHaveBeenCalled();
  });

  it('does not PATCH when the card stays in its lane', () => {
    const { result } = renderHook(() => useLeadsBoard(initial));
    dragTo(result, 'a', 'b'); // reorder within PENDING
    expect(fetch).not.toHaveBeenCalled();
  });
});
