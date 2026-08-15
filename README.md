# Lead Management Application

A take-home assignment: a public form where prospects submit their name, email,
and resume, and an authenticated internal UI where attorneys review and manage
those leads.

- **Backend:** FastAPI + SQLAlchemy + Alembic (SQLite), JWT auth, MinIO/S3 for
  resumes, Resend (or console) for email.
- **Frontend:** Next.js (App Router, TypeScript) — public lead form +
  auth-guarded attorney UI.
- **Infra:** Docker Compose orchestrates the frontend, backend, MinIO, and a
  one-shot bucket-creation job.

See [`docs/system-design.md`](docs/system-design.md) for the full design and
the reasoning behind each choice.

---

## Run it locally

**Prerequisites:** Docker with the Compose plugin (`docker compose version`),
and `make` (preinstalled on macOS/Linux).

First-time setup (builds the stack, waits for the backend to be healthy,
then seeds demo leads, resumes, and activity):

```bash
cp .env.example .env
make setup
```

Then open **http://localhost:3300**.

- `make setup` — first-time command. Brings the stack up **and** populates
  demo data.
- `make seed` — only populates demo data, assuming the stack is already
  running. The seed is idempotent: it skips if leads already exist.

The default `.env` runs the whole app with **no real secrets**: emails are
logged to the backend console instead of being sent, and admin accounts are
seeded for login.

To wipe everything (database + resumes) and start fresh:

```bash
docker compose down -v
make setup
```

### Log in to the attorney UI

Go to **http://localhost:3300/login**. Any of these seeded accounts works —
they all share the password `password`:

- `admin@tryalma.com` (the main one)
- `attorney@tryalma.com`
- `paralegal@tryalma.com`

(These come from `ADMIN_EMAIL` / `EXTRA_ADMIN_EMAILS` in `.env`, seeded
idempotently on startup. The extra accounts exist so the activity feed shows
actions attributed to different people.)

### Try the end-to-end flow

1. On the home page (`/`), submit the form with a name, email, and a resume
   (`.pdf`, `.doc`, or `.docx`, ≤ 10 MB).
2. Check the backend logs for the two emails (prospect confirmation + attorney
   notification): `docker compose logs -f backend`.
3. Log in at `/login`, view the new lead in `/leads`, open it, download the
   resume, and mark it **REACHED_OUT**.

### Send real email (optional)

Edit `.env`:

```
EMAIL_PROVIDER=resend
RESEND_API_KEY=re_your_real_key
EMAIL_FROM="You <you@your-verified-domain.com>"
```

Restart the backend: `docker compose up --build backend`. Without a verified
sending domain, Resend's default `onboarding@resend.dev` only delivers to your
own Resend account email.

---

## Services & ports

| URL                          | What                                  |
|------------------------------|---------------------------------------|
| http://localhost:3300        | Frontend (public form + attorney UI)  |
| http://localhost:8800/docs   | FastAPI OpenAPI docs                  |
| http://localhost:9901        | MinIO console (`minioadmin`/`minioadmin`) |

> **Near-default ports:** the app uses `3300` (frontend), `8800` (backend),
> and `9900`/`9901` (MinIO) — the familiar `3xxx`/`8xxx`/`9xxx` ranges, just
> off the exact defaults `3000`/`8000`/`9000`, so it won't collide with other
> things you might already have running locally.

The browser only ever talks to the frontend on `:3300`; Next.js proxies
`/api/*` to the backend server-side. Port 9900 is published so the browser can
follow pre-signed resume-download URLs.

## Data persistence

Resumes and the SQLite database live in named Docker volumes (`minio-data`,
`sqlite-data`), so they survive `docker compose down`. See
[Run it locally](#run-it-locally) above for how to wipe them and start fresh.

---

## Repository layout

```
backend/     FastAPI app (app/), Alembic migrations, pytest tests
frontend/    Next.js app (App Router)
docs/        system-design.md and other documentation
docker-compose.yml
.env.example
```

## Tests

Backend (requires Python 3.12+):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest tests/test_api.py
```

The tests stub out object storage and email, so they run without MinIO or
network access.
