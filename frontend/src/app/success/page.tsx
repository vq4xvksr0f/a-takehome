import Link from 'next/link';
import shared from '@/styles/shared.module.css';
import styles from './success.module.css';

export default function SuccessPage() {
  return (
    <main className={styles['success-page']}>
      <div className={`${shared.card} ${styles['success-card']}`}>
        <span className={styles['success-icon']} aria-hidden="true">
          ✓
        </span>
        <h1 className={styles['success-title']}>Thank you</h1>
        <p className={styles['success-message']}>
          Your application has been received. An attorney will personally review
          your submission and reach out within 1–2 business days.
        </p>
        <Link href="/" className={`${shared.btn} ${shared['btn-secondary']} ${shared['btn-block']}`}>
          Back to home
        </Link>
      </div>
    </main>
  );
}
