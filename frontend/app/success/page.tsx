import Link from 'next/link';

export default function SuccessPage() {
  return (
    <main className="centered-page">
      <div className="card form-card">
        <h1 className="page-title">Thank you</h1>
        <p className="page-subtitle">
          Your information has been received. An attorney will review your
          submission and reach out to you shortly.
        </p>
        <Link href="/" className="btn btn-secondary btn-block">
          Submit another application
        </Link>
      </div>
    </main>
  );
}
