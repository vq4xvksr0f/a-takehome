import Link from 'next/link';
import { redirect } from 'next/navigation';
import { apiFetch, LeadSummary } from '@/lib/api';
import LogoutButton from './LogoutButton';

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
    <main className="page">
      <header className="page-header">
        <div>
          <h1 className="page-title">Leads</h1>
          <p className="page-subtitle">Prospective clients submitted through the public form.</p>
        </div>
        <LogoutButton />
      </header>

      {leads.length === 0 ? (
        <div className="card empty-state">
          <p>No leads yet. New submissions from the public form will appear here.</p>
        </div>
      ) : (
        <div className="card table-card">
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>State</th>
                <th>Submitted</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => (
                <tr key={lead.id}>
                  <td>
                    <Link href={`/leads/${lead.id}`} className="row-link">
                      {lead.first_name} {lead.last_name}
                    </Link>
                  </td>
                  <td>{lead.email}</td>
                  <td>
                    <span
                      className={`badge ${
                        lead.state === 'REACHED_OUT'
                          ? 'badge-reached-out'
                          : 'badge-pending'
                      }`}
                    >
                      {lead.state === 'REACHED_OUT' ? 'Reached out' : 'Pending'}
                    </span>
                  </td>
                  <td>{formatDate(lead.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
