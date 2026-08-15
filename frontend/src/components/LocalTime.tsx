'use client';

import { formatDate } from '@/lib/format';

/**
 * Renders an ISO timestamp in the viewer's local timezone. Must be a client
 * component: the server renders in UTC, so formatting here picks up the
 * browser's TZ.
 */
export default function LocalTime({ iso }: { iso: string }) {
  return <>{formatDate(iso)}</>;
}
