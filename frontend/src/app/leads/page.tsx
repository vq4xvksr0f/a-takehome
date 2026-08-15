import { redirect } from 'next/navigation';
import { apiFetch } from '@/server/api-client';
import type { LeadSummary } from '@/types/lead';
import AttorneyHeader from '@/components/auth/AttorneyHeader';
import LeadsBoard from './LeadsBoard';
import layoutStyles from './leads-layout.module.css';
import shared from '@/styles/shared.module.css';

export default async function LeadsPage() {
  const res = await apiFetch('/api/leads');

  if (res.status === 401) {
    redirect('/login');
  }
  if (!res.ok) {
    throw new Error(`Failed to load leads (${res.status})`);
  }

  const body = await res.json();
  // Tolerate both a bare array and a paginated envelope like {items: [...]}.
  const leads: LeadSummary[] = Array.isArray(body) ? body : body.items ?? [];

  return (
    <main className={layoutStyles.page}>
      <header className={layoutStyles['page-header']}>
        <div>
          <h1 className={shared['page-title']}>Leads</h1>
          <p className={shared['page-subtitle']}>
            Prospective clients submitted through the public form. Drag a card to
            mark it reached out.
          </p>
        </div>
        <AttorneyHeader />
      </header>

      <LeadsBoard initialLeads={leads} />
    </main>
  );
}
