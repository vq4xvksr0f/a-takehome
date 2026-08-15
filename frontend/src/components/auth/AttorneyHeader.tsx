import { getCurrentAttorneyEmail } from '@/server/current-attorney';
import AccountMenu from './AccountMenu';

/**
 * Header for attorney pages: a compact account menu (avatar) in the top-right.
 * Server component — the email comes from the JWT cookie, never from client JS.
 */
export default function AttorneyHeader() {
  const email = getCurrentAttorneyEmail();
  if (!email) return null;

  return (
    <div className="attorney-header">
      <AccountMenu email={email} />
    </div>
  );
}
