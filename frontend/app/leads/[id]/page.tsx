import Link from 'next/link';
import { notFound, redirect } from 'next/navigation';
import { apiFetch, Lead } from '@/lib/api';
import LogoutButton from '../LogoutButton';
import MarkReachedOutButton from '../MarkReachedOutButton';

function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

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
    <main className="page">
      <header className="page-header">
        <div>
          <Link href="/leads" className="back-link">
            ← Back to leads
          </Link>
          <h1 className="page-title">
            {lead.first_name} {lead.last_name}
          </h1>
        </div>
        <LogoutButton />
      </header>

      <div className="card detail-card">
        <dl className="detail-grid">
          <div className="detail-item">
            <dt>First name</dt>
            <dd>{lead.first_name}</dd>
          </div>
          <div className="detail-item">
            <dt>Last name</dt>
            <dd>{lead.last_name}</dd>
          </div>
          <div className="detail-item">
            <dt>Email</dt>
            <dd>{lead.email}</dd>
          </div>
          <div className="detail-item">
            <dt>State</dt>
            <dd>
              <span
                className={`badge ${
                  lead.state === 'REACHED_OUT' ? 'badge-reached-out' : 'badge-pending'
                }`}
              >
                {lead.state === 'REACHED_OUT' ? 'Reached out' : 'Pending'}
              </span>
            </dd>
          </div>
          <div className="detail-item">
            <dt>Resume</dt>
            <dd>
              {lead.resume_filename}{' '}
              {/* Plain anchor: the backend 302-redirects to a pre-signed
                  download URL, and the browser follows it natively. */}
              <a href={`/api/leads/${lead.id}/resume`} className="text-link">
                Download
              </a>
            </dd>
          </div>
          <div className="detail-item">
            <dt>Submitted</dt>
            <dd>{formatDate(lead.created_at)}</dd>
          </div>
          <div className="detail-item">
            <dt>Last updated</dt>
            <dd>{formatDate(lead.updated_at)}</dd>
          </div>
        </dl>

        <div className="detail-actions">
          <MarkReachedOutButton leadId={lead.id} initialState={lead.state} />
        </div>
      </div>
    </main>
  );
}
