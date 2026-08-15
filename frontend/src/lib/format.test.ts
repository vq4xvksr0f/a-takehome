import { describe, expect, it } from 'vitest';
import { formatDate } from './format';

describe('formatDate', () => {
  it('formats an ISO timestamp into a readable en-US string', () => {
    // toLocaleString output is locale/timezone dependent; assert shape, not
    // exact text: "Aug 15, 2026, <time>".
    const out = formatDate('2026-08-15T02:07:44+00:00');
    expect(out).toMatch(/Aug 15, 202[56]/);
    expect(out).toMatch(/\d{1,2}:\d{2}/);
  });

  it('returns invalid input unchanged', () => {
    expect(formatDate('not-a-date')).toBe('not-a-date');
  });
});
