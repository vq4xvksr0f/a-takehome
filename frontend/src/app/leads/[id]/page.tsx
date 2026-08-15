import Link from 'next/link';
import { notFound, redirect } from 'next/navigation';
import { apiFetch } from '@/server/api-client';
import { formatDate } from '@/lib/format';
import type { Lead } from '@/types/lead';
import AttorneyHeader from '@/components/auth/AttorneyHeader';
import StateBadge from '../StateBadge';
import StateToggleButton from './StateToggleButton';
import layoutStyles from '../leads-layout.module.css';
import shared from '@/styles/shared.module.css';
import detailStyles from './detail.module.css';

export default async function LeadDetailPage({ params }: { params: { id: string } }) {
  const res = await apiFetch(`/api/leads/${params.id}`);

  if (res.status === 401) {
    redirect('/login');
  }
  if (res.status === 404) {
    notFound();
  }
  if (!res.ok) {
    throw new Error(`Failed to load lead (${res.status})`);
  }

  const lead: Lead = await res.json();

  return (
    <main className={layoutStyles.page}>
      <header className={layoutStyles['page-header']}>
        <div>
          <Link href="/leads" className={layoutStyles['back-link']}>
            ← Back to leads
          </Link>
          <h1 className={shared['page-title']}>
            {lead.first_name} {lead.last_name}
          </h1>
        </div>
        <AttorneyHeader />
      </header>

      <div className={`${shared.card} ${detailStyles['detail-card']}`}>
        <dl className={detailStyles['detail-grid']}>
          <div className={detailStyles['detail-item']}>
            <dt>First name</dt>
            <dd>{lead.first_name}</dd>
          </div>
          <div className={detailStyles['detail-item']}>
            <dt>Last name</dt>
            <dd>{lead.last_name}</dd>
          </div>
          <div className={detailStyles['detail-item']}>
            <dt>Email</dt>
            <dd>{lead.email}</dd>
          </div>
          <div className={detailStyles['detail-item']}>
            <dt>State</dt>
            <dd>
              <StateBadge state={lead.state} />
            </dd>
          </div>
          <div className={detailStyles['detail-item']}>
            <dt>Resume</dt>
            <dd>
              {lead.resume_filename}{' '}
              {/* Plain anchor: the backend 302-redirects to a pre-signed
                  download URL, and the browser follows it natively. */}
              <a href={`/api/leads/${lead.id}/resume`} className={detailStyles['text-link']}>
                Download
              </a>
            </dd>
          </div>
          <div className={detailStyles['detail-item']}>
            <dt>Submitted</dt>
            <dd>{formatDate(lead.created_at)}</dd>
          </div>
          <div className={detailStyles['detail-item']}>
            <dt>Last updated</dt>
            <dd>{formatDate(lead.updated_at)}</dd>
          </div>
        </dl>

        <div className={detailStyles['detail-actions']}>
          <StateToggleButton leadId={lead.id} initialState={lead.state} />
        </div>
      </div>
    </main>
  );
}
