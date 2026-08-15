import LeadForm from './LeadForm';
import styles from './page.module.css';

export default function LeadFormPage() {
  return (
    <main className={styles['split-page']}>
      <aside className={styles['promo-pane']}>
        <div className={styles['promo-inner']}>
          <p className={styles['promo-brand']}>Alma</p>
          <h1 className={styles['promo-headline']}>Get a free case evaluation.</h1>
          <p className={styles['promo-lede']}>
            Send us your details and resume. An attorney will personally review
            your submission and let you know how we can help.
          </p>
          <ul className={styles['promo-points']}>
            <li>
              <strong>Reviewed by a licensed attorney</strong>
              <span>Every submission is read by a person, not a bot.</span>
            </li>
            <li>
              <strong>Response in 1–2 business days</strong>
              <span>We reach out by email once your case is reviewed.</span>
            </li>
            <li>
              <strong>Confidential</strong>
              <span>Your information stays between you and the firm.</span>
            </li>
          </ul>
        </div>
      </aside>

      <section className={styles['form-pane']}>
        <LeadForm />
      </section>
    </main>
  );
}
