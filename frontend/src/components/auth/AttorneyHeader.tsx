import { getCurrentAttorneyEmail } from '@/server/current-attorney';
import AccountMenu from './AccountMenu';
import styles from './AccountMenu.module.css';

/**
 * Header for attorney pages: a compact account menu (avatar) in the top-right.
 * Server component — the email comes from the JWT cookie, never from client JS.
 */
export default function AttorneyHeader() {
  const email = getCurrentAttorneyEmail();
  if (!email) return null;

  return (
    <div className={styles['attorney-header']}>
      <AccountMenu email={email} />
    </div>
  );
}
