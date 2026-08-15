# System Design — Lead Management Application

A take-home design document for a lead management system: a public form where
prospects submit their contact details and resume, and an authenticated
internal UI where attorneys review and manage those leads.

The guiding principle: **solve the requirements well, don't gold-plate.** Every
choice below is the simplest one that still demonstrates production thinking
(clear boundaries, swappable dependencies, sane security).

---

## 1. Architecture Overview

Three runtime components, orchestrated with Docker Compose:

- **Next.js frontend** — serves the public lead-submission page and the
  authenticated attorney UI. Communicates with the backend over HTTP only; it
  never touches the database or object storage directly.
- **FastAPI backend** — the single source of truth. Exposes a REST API, owns
  business logic, persists lead records, streams resume uploads to object
  storage, sends emails, and issues/validates JWTs.
- **Infrastructure services** — SQLite (embedded in the backend container,
  file on a named volume) and MinIO (S3-compatible object storage, data on a
  named volume).

The backend is deliberately structured around **ports and adapters** (thin
interfaces around the database, file storage, and email sending) so SQLite can
be swapped for PostgreSQL, and MinIO for AWS S3, without touching business
logic.

**Same-origin rule:** the browser talks to Next.js (`:3000`) only. All
`/api/*` requests are forwarded server-side by Next.js (via `rewrites()` or a
route handler) to `http://backend:8000` on the internal Compose network. This
is what makes the JWT cookie model work: the cookie is first-party on
`localhost:3000`, so Next.js middleware/server components can read it, the
proxy forwards it to FastAPI, and no cross-origin CORS/credentials complexity
is needed. Port 8000 stays reachable on the host for direct API inspection
(`curl`, the auto-generated OpenAPI docs at `/docs`), but the frontend never
depends on it.

```
                        ┌──────────────────────────────────────────┐
                        │            Docker Compose network         │
                        │                                          │
 Browser                │                                          │
   │ :3000 only         │   ┌──────────────┐    ┌───────────────┐  │
   │                    │   │   Next.js    │    │    FastAPI    │  │
   ├────────────────────┼──▶│   frontend   │───▶│    backend    │  │
   │                    │   │   (port 3000)│    │  (port 8000)  │  │
   │                    │   └──────────────┘    └───┬───────┬───┘  │
   │                    │       proxies /api/*      │       │      │
   │                    │                    ┌──────▼──┐ ┌──▼─────┐│
   │                    │                    │ SQLite  │ │ MinIO  ││
   │                    │                    │ (volume)│ │(volume)││
   │                    │                    └─────────┘ └────────┘│
   │                    └──────────────────────────────────────────┘
   │
   └── FastAPI calls Resend (external HTTPS API) for email delivery
```

## 2. Component Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                              Next.js (3000)                            │
│  ┌───────────────────────┐        ┌─────────────────────────────────┐  │
│  │ Public pages          │        │ Attorney pages (auth required)  │  │
│  │  /            (form)  │        │  /login    /leads   /leads/[id] │  │
│  └──────────┬────────────┘        └─────────────────┬───────────────┘  │
│             │ multipart/form-data                   │ JWT cookie       │
└─────────────┼───────────────────────────────────────┼──────────────────┘
              ▼                                       ▼
   (browser → same-origin /api/* → Next.js proxies to FastAPI,
    forwarding the HttpOnly cookie; browser never calls :8000 directly)
┌────────────────────────────────────────────────────────────────────────┐
│                              FastAPI (8000)                            │
│                                                                        │
│  API layer      routers: leads, auth, resumes                         │
│  Service layer  LeadService, EmailService, AuthService                │
│  Adapters       Repository (SQLAlchemy) │ ObjectStore (boto3) │       │
│                 EmailClient (Resend HTTPS API)                        │
│  Cross-cutting  JWT auth dependency, validation (Pydantic),           │
│                 centralized error handlers, structured logging        │
└──────┬───────────────────────┬───────────────────────┬─────────────────┘
       ▼                       ▼                       ▼
┌─────────────┐      ┌──────────────────┐      ┌──────────────────┐
│   SQLite    │      │   MinIO (9000)   │      │  Resend API      │
│  leads.db   │      │  bucket: resumes │      │  (external HTTPS)│
│  (volume)   │      │  (volume)        │      │                  │
└─────────────┘      └──────────────────┘      └──────────────────┘
```

## 3. Data Flow — Public Lead Submission

1. Prospect fills the form on `/` (first name, last name, email, resume file)
   and submits. The frontend POSTs `multipart/form-data` to
   `POST /api/leads`.
2. FastAPI validates the payload with Pydantic (name lengths, email format,
   file extension allow-list: `.pdf`, `.doc`, `.docx`; size cap, e.g. 10 MB).
3. **Persist the resume first**: the backend streams the upload to MinIO under
   a generated object key `resumes/{uuid}.{ext}` (server-generated key, never
   client-controlled).
4. **Persist the lead**: insert a row into `leads` with state `PENDING` and
   the object key (not the binary) as `resume_object_key`.
5. If step 4 fails after step 3 succeeded, delete the orphaned object
   (best-effort cleanup).
6. **Send emails** (after the transaction commits):
   - Confirmation to the prospect ("we received your application").
   - Notification to the attorney inbox ("new lead: name, email").
7. Return `201 Created` with the lead's public fields. The frontend shows a
   success confirmation.

Email failures are logged and surfaced in server logs, but do **not** fail the
request — the lead is durably persisted, and the prospect's UX should not
depend on an external email provider's availability. (See §11 for the full
rationale.)

## 4. Data Flow — Attorney Login

1. Attorney submits email + password on `/login`; the browser POSTs JSON to
   `/api/auth/login` — which Next.js proxies server-side to FastAPI.
2. FastAPI looks up the attorney by email and verifies the password against
   the stored **bcrypt hash** (constant-time comparison via `passlib` /
   `bcrypt`).
3. On success the backend issues a short-lived **signed JWT** (see §8) in a
   `Set-Cookie` header. Because the request arrived same-origin via the
   Next.js proxy, the cookie is set **for `localhost:3000`** — first-party to
   the frontend. The proxy passes the `Set-Cookie` header through untouched.
4. The browser stores the **`HttpOnly`, `Secure`, `SameSite=Lax`** cookie
   (invisible to JavaScript) and the app redirects to `/leads`.
5. Subsequent requests to `/api/*` carry the cookie automatically, and the
   Next.js proxy forwards it to FastAPI. Next.js **middleware** (and server
   components) can also read the same cookie — it's on the frontend's origin —
   so unauthenticated users are redirected to `/login` before any attorney
   page renders.

Attorney accounts are provisioned by an **idempotent seed on backend
startup**: after migrations run, the app reads `ADMIN_EMAIL` and
`ADMIN_PASSWORD` from the environment and ensures that attorney exists
(bcrypt-hashed, created only if missing). `.env.example` ships
`ADMIN_EMAIL=admin@tryalma.com` / `ADMIN_PASSWORD=password` as the defaults,
so `cp .env.example .env` still gives a reviewer a working login with zero
configuration — but the credentials live in config, not source code. No
public registration endpoint exists.

## 5. Data Flow — Viewing & Updating Leads

**List leads** — `GET /api/leads`:
- Frontend (attorney page, authenticated) requests the list.
- Backend validates the JWT, queries `leads` ordered by `created_at DESC`,
  returns paginated summaries (id, name, email, state, created_at).

**View lead detail** — `GET /api/leads/{id}`:
- Returns all submitted fields plus state and timestamps.

**Download resume** — `GET /api/leads/{id}/resume`:
- Backend validates the JWT, looks up `resume_object_key`, generates a
  short-lived (e.g. 60s) **pre-signed GET URL** from MinIO/S3, and returns a
  redirect (302) to it.
- The browser downloads directly from object storage — the file bytes never
  pass through the FastAPI process, and MinIO itself is never exposed publicly
  without a signature.

**Update state** — `PATCH /api/leads/{id}` with `{ "state": "PENDING" | "REACHED_OUT" }`:
- Backend validates the JWT, loads the lead, checks the transition is legal
  (`PENDING ↔ REACHED_OUT`; unknown states and no-op transitions to the current
  state → `409 Conflict`), updates the row, returns the updated lead.
- A lead moves between `PENDING` and `REACHED_OUT` in either direction. The
  board exposes both directions via drag-and-drop; the detail page offers a
  toggle button.

## 6. Database Schema

SQLite, accessed through **SQLAlchemy 2.x** with **Alembic** migrations.
Using an ORM + migrations from day one is what makes the later
SQLite → PostgreSQL swap a config change instead of a rewrite.

```sql
CREATE TABLE leads (
    id                  TEXT PRIMARY KEY,            -- UUID4
    first_name          TEXT NOT NULL,
    last_name           TEXT NOT NULL,
    email               TEXT NOT NULL,
    state               TEXT NOT NULL DEFAULT 'PENDING'
                        CHECK (state IN ('PENDING', 'REACHED_OUT')),
    resume_object_key   TEXT NOT NULL,               -- e.g. resumes/<uuid>.pdf
    resume_filename     TEXT NOT NULL,               -- original filename, for display
    created_at          TEXT NOT NULL,               -- ISO-8601 UTC
    updated_at          TEXT NOT NULL
);
CREATE INDEX idx_leads_created_at ON leads (created_at DESC);
CREATE INDEX idx_leads_state      ON leads (state);

CREATE TABLE attorneys (
    id              TEXT PRIMARY KEY,                -- UUID4
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,                   -- bcrypt
    created_at      TEXT NOT NULL
);

-- Outbox pattern (§9): DOCUMENTED, not implemented in the take-home.
-- Kept minimal on purpose — just enough to show the shape.
CREATE TABLE email_outbox (
    id              TEXT PRIMARY KEY,                -- UUID4
    lead_id         TEXT NOT NULL REFERENCES leads (id),
    recipient       TEXT NOT NULL,                   -- to-address
    subject         TEXT NOT NULL,
    html            TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'sent', 'failed')),
    created_at      TEXT NOT NULL                    -- ISO-8601 UTC
);
```

Notes:

- `state` is a `TEXT` with a `CHECK` constraint rather than a DB-native enum —
  portable between SQLite and PostgreSQL. The authoritative transition logic
  lives in the service layer.
- Email is **not** unique on `leads`: the same person may apply twice; the
  assignment doesn't call for deduplication.
- UUID primary keys avoid SQLite autoincrement quirks and leak nothing about
  record counts.
- `email_outbox` is the **transactional outbox** (§9): rows would be inserted
  in the same transaction as the `leads` row, so a lead is never persisted
  without its emails being durably queued. In the take-home it's defined only
  to show the shape — emails are actually sent best-effort after commit
  (§11), and the outbox is the documented upgrade path (§14).

## 7. Resume / File-Storage Design

**Why not store the file binary in SQLite?**

- **Bloat and backup pain**: a few multi-MB PDFs would dwarf the row data,
  inflating the single database file and every backup/snapshot of it.
- **Read amplification**: listing or fetching leads would share a database
  file (and connection pool) with large binary reads; SQLite's single-writer
  model makes this contention worse.
- **Wrong tool for the job**: databases are optimized for structured,
  queryable data; object storage is optimized for immutable blobs, and gives
  us streaming, content-type metadata, and pre-signed URLs for free.
- **Portability**: with the binary in S3-compatible storage, moving SQLite →
  PostgreSQL later means migrating only small structured rows.

**Design:**

- The DB stores only `resume_object_key` + display filename; bytes live in a
  `resumes` bucket in MinIO.
- Object keys are server-generated UUIDs (path-traversal-safe, collision-free,
  and they decouple storage from the original filename, which may contain
  arbitrary user input).
- Uploads are validated (extension allow-list, size cap) and **streamed** to
  MinIO via the S3 API (`boto3`) rather than buffered fully in memory.
- Downloads use **pre-signed URLs** (see §5): MinIO stays on the internal
  Docker network, unreachable from the browser except via a signed,
  expiring URL issued to an authenticated attorney.
- **Swappability**: all S3 access goes through a thin `ObjectStore` interface
  (`put`, `delete`, `presigned_get_url`) configured by env vars
  (`S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`).
  Locally these point at MinIO; in production the same code points at AWS S3
  by changing env vars only. That is the entire reason MinIO was chosen: it
  speaks the S3 API, so the production migration path is zero-code.
- MinIO's data directory is backed by a **named Docker volume**
  (`minio-data`), so resumes survive `docker compose down` / restarts. A
  one-shot `createbucket` init container creates the bucket on startup.

## 8. Authentication / JWT Design

**Token contents:** standard claims only — `sub` (attorney id), `email`,
`iat`, `exp` (e.g. 8 hours). Signed with **HS256** using `JWT_SECRET_KEY`
from the environment. No sensitive data in the payload (JWTs are signed, not
encrypted — anyone can read them).

**Client-side storage:** the JWT lives in an **`HttpOnly` cookie**
(`SameSite=Lax`), scoped to the **frontend origin** (`localhost:3000`) —
never in `localStorage`, and never on the FastAPI origin. Rationale:

- `localStorage` tokens are readable by any JavaScript running on the page —
  one XSS and the token is gone. An `HttpOnly` cookie is invisible to
  JavaScript entirely.
- Scoping the cookie to `:3000` is what lets Next.js middleware and server
  components read it for auth-gating, while the `/api` proxy forwards it to
  FastAPI. (If the cookie were set on `:8000`, the browser would treat it as
  a different origin and never send it to Next.js — the same-origin proxy in
  §1 exists precisely to avoid that.)
- `SameSite=Lax` blocks the cookie on cross-site POSTs, which mitigates CSRF
  for our state-changing endpoints. (A note for hardening: if we ever move to
  `SameSite=None`/cross-origin deployments, we must add explicit CSRF tokens.)
- **`Secure` is env-driven, off locally.** The cookie is set with
  `Secure` only when `COOKIE_SECURE=true` (production, behind HTTPS). On
  local plain-HTTP we deliberately omit it: although Chrome treats
  `localhost` as a secure context, a reviewer hitting the app via
  `http://127.0.0.1:3000`, a LAN IP, or a stricter browser could otherwise
  have the cookie silently rejected — login would "succeed" yet never stick,
  with no error shown. Omitting `Secure` locally removes that failure mode
  entirely; the flag is switched on at the same time HTTPS is (§14).

**Server-side validation:** a FastAPI dependency (`get_current_attorney`)
extracts the cookie, verifies the signature and `exp` using `python-jose` /
`pyjwt`, loads the attorney id from `sub`, and rejects with `401` on any
failure (missing, expired, bad signature, unknown subject). Attorney routes
declare the dependency; public routes don't.

**Why JWTs don't need to be persisted in the database:** the signature makes
the token self-verifying. Validation is purely cryptographic — recompute the
HMAC over the header/payload with the secret and compare — so there is no
server-side session table to query on every request. The trade-off is that
tokens can't be individually revoked before expiry; we accept that here and
mitigate it with a short `exp`. (If revocation is ever needed, add a token
version column on `attorneys` or a denylist — deliberately out of scope.)

**Passwords:** bcrypt hashes only; never logged; the seeded admin's plaintext
password exists only as a documented take-home default.

## 9. Email Integration

- **Provider:** Resend, via its HTTPS API (official `resend` Python SDK).
- All sending goes through a thin `EmailClient` interface
  (`send(to, subject, html)`) so the provider could be swapped without
  touching call sites.
- **Two sends per submission** (§3): prospect confirmation and attorney
  notification. Both are plain, transactional templates rendered server-side.
- **Failure policy:** email send happens *after* the lead transaction commits
  and is wrapped so failures are logged (with the lead id) but never turn a
  successful submission into a 5xx. Rationale: email is best-effort
  notification; the lead record is the source of truth. Documented as a
  conscious trade-off — a production system would add a retry queue
  (e.g. Celery/SQS), which is unnecessary complexity for a take-home.
- **Local fallback (`EMAIL_PROVIDER=console`):** if no `RESEND_API_KEY` is
  set, the `EmailClient` logs the rendered email (to, subject, body) instead
  of calling Resend. A reviewer without a key still sees the full
  submission → confirmation → notification flow work end-to-end in the
  backend logs. With a real key present, the same code path sends for real.
  This is just a second implementation of the same `EmailClient` interface.
- **Outbox pattern (documented, not implemented):** the one real hole in the
  best-effort policy above is "lead committed, but the email send failed and
  is now lost." The production-grade fix is a **transactional outbox**: write
  the email as a row in an `email_outbox` table *in the same DB transaction*
  as the lead insert, then have a background worker read pending rows and
  (re)send them. This makes lead-write and email-enqueue atomic — you can
  never persist a lead without its emails being durably queued — and turns
  provider outages into automatic retries. For a take-home this is exactly
  the right idea to *name* without building a worker; the schema would be a
  small `(id, to, subject, html, status, attempts, created_at)` table, and
  the worker a loop over `status='pending'`. Flagged here so the design shows
  the thinking; deliberately out of scope for the implementation.
- **Secrets handling:** `RESEND_API_KEY`, the from-address
  (`EMAIL_FROM`), and the attorney notification inbox
  (`ATTORNEY_NOTIFY_EMAIL`) come from environment variables via `.env`
  (git-ignored) → `docker-compose.yml` → the backend container.
  `.env.example` documents every variable with placeholder values; real keys
  are never committed. The API key is only ever used server-side — it never
  reaches the Next.js client bundle.

## 10. API Design

Base URL `/api`. JSON everywhere except the upload (multipart) and the resume
download (redirect). Public endpoints are unauthenticated; everything else
requires the JWT cookie.

| Method | Path                        | Auth   | Description                                   |
|--------|-----------------------------|--------|-----------------------------------------------|
| POST   | `/api/leads`                | Public | Submit lead (multipart: fields + resume file) |
| POST   | `/api/auth/login`           | Public | Email + password → sets JWT cookie            |
| POST   | `/api/auth/logout`          | Public | Clears the JWT cookie                         |
| GET    | `/api/leads`                | JWT    | Paginated list of leads (summary fields)      |
| GET    | `/api/leads/{id}`           | JWT    | Full lead detail                              |
| GET    | `/api/leads/{id}/resume`    | JWT    | 302 → pre-signed MinIO/S3 download URL        |
| PATCH  | `/api/leads/{id}`           | JWT    | Body `{state}`; move between PENDING/REACHED_OUT |
| GET    | `/api/health`               | Public | Liveness probe (used by Compose healthcheck)  |

Conventions: UUIDs in path params; `201` on creation; pagination via
`?limit=&offset=`; error responses use a consistent shape (§11).

## 11. Error Handling

- **Consistent error envelope** for all 4xx/5xx:
  `{ "detail": "human-readable message", "code": "MACHINE_READABLE_CODE" }`.
- **Validation errors** (Pydantic): `422` with field-level messages; the
  frontend maps them onto form fields.
- **Auth failures**: `401` (no/invalid/expired token, bad credentials —
  deliberately indistinguishable for login), `403` reserved for
  authenticated-but-forbidden (currently unused; single role).
- **Not found**: `404` for unknown lead ids.
- **Illegal state transition**: `409 Conflict` (unknown state value, or a
  no-op PATCH to the lead's current state).
- **Upload violations**: `413` (too large), `415` (unsupported media type).
- **Unexpected errors**: a global exception handler logs the full traceback
  server-side and returns a generic `500` — internals never leak to clients.
- **Partial-failure policy on submission** (§3): DB insert failure after a
  successful upload triggers best-effort deletion of the orphan object; email
  failure after commit is logged, not propagated.

## 12. Security Considerations

- **Authentication**: bcrypt password hashing; JWT in `HttpOnly`/
  `SameSite=Lax` cookie; no token in `localStorage`; short token lifetime;
  no public registration.
- **Input validation**: Pydantic on every field; email format check; length
  caps on names.
- **File upload safety**: extension allow-list (`.pdf/.doc/.docx`), size cap,
  server-generated object keys (no path traversal, no user-controlled
  filenames in storage), files served only via expiring pre-signed URLs.
- **SQL injection**: SQLAlchemy parameterized queries everywhere; no raw SQL.
- **XSS**: React escapes rendered content by default; no `dangerouslySetInnerHTML`.
- **CORS**: the browser only ever calls the same-origin Next.js proxy, so
  browser-driven CORS effectively doesn't arise. FastAPI still sets a narrow
  `CORSMiddleware` policy (allow `http://localhost:3300`, credentials on) as
  defense-in-depth for direct backend access; never `*` with credentials.
- **Secrets**: all in env vars / git-ignored `.env`; `.env.example` contains
  placeholders only; nothing sensitive baked into images.
- **Rate limiting**: noted as a production gap — a public form is a spam
  target. Deliberately out of scope locally; production answer is a
  reverse-proxy/WAF limit or a simple middleware plus CAPTCHA.
- **HTTPS**: terminated at the proxy/load balancer in production, at which
  point `COOKIE_SECURE=true` adds the `Secure` flag. Local dev runs plain
  HTTP with the flag off so the cookie is never silently rejected (§8).

## 13. Docker / Local Development Architecture

Goal: `cp .env.example .env && docker compose up --build` gives a working
system. Four services:

| Service    | Image/build         | Host port    | Notes                                             |
|------------|--------------------|--------------|---------------------------------------------------|
| `frontend` | Next.js Dockerfile  | **3300**     | Multi-stage build; proxies `/api/*` → `http://backend:8000` (server-side, via `rewrites()`); browser calls only the frontend |
| `backend`  | FastAPI Dockerfile  | **8800**     | Runs Alembic migrations + seed on startup         |
| `minio`    | `minio/minio`       | **9900**, **9901** | 9900 = S3 API (published so the browser can reach pre-signed URLs); 9901 = console; volume `minio-data` |
| `createbuckets` | `minio/mc` (one-shot) | —      | Creates the `resumes` bucket, then exits          |

> **Near-default host ports.** Host-facing ports sit in the familiar
> `3xxx`/`8xxx`/`9xxx` ranges — `3300`/`8800`/`9900`/`9901` — just off the
> exact defaults (`3000`/`8000`/`9000`/`9001`), because a reviewer is likely
> to already have something occupying the standard ports. Only the host-side
> published port changes; container-internal ports stay standard, so the proxy
> target, CORS origin, and pre-signed endpoint all move together.

- **Volumes**: `minio-data` (resumes persist across restarts) and
  `sqlite-data` (the `leads.db` file) — both named volumes.
- **Networking**: all services on one Compose network. The **frontend (host
  port 3300)** is the only one the app strictly needs on the host. MinIO's S3
  API (host port **9900**) is also published because resume downloads work by
  the backend issuing a **pre-signed URL the browser follows directly to
  MinIO** — that URL must be reachable from the browser, so it's generated
  against the public host (`S3_PUBLIC_ENDPOINT=http://localhost:9900`,
  distinct from the internal `S3_ENDPOINT_URL=http://minio:9000` the backend
  uses for uploads). MinIO is still not *browsable* without a signature —
  bucket listing and arbitrary reads stay denied; only a specific, expiring,
  signed GET works. The backend (8800) and MinIO console (9901) are optional
  debug conveniences (OpenAPI docs, MinIO console).
- **Env**: a single `.env` at the repo root feeds Compose variable
  substitution; `.env.example` documents every key
  (`JWT_SECRET_KEY`, `RESEND_API_KEY`, `EMAIL_FROM`, `EMAIL_PROVIDER`,
  `ATTORNEY_NOTIFY_EMAIL`, `S3_ENDPOINT_URL`, `S3_PUBLIC_ENDPOINT`,
  `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`, `DATABASE_URL`,
  `COOKIE_SECURE`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`). `.env.example` ships
  working defaults for the admin seed (`admin@tryalma.com` / `password`) and
  `EMAIL_PROVIDER=console`, so a bare `cp .env.example .env` runs the whole
  app with no real secrets; only `RESEND_API_KEY` needs a real value to send
  actual email.
- **Health/ordering**: `depends_on` with healthchecks so the backend starts
  after MinIO and the bucket exist.
- **Hot reload** for local development via bind mounts + `uvicorn --reload`
  / `next dev` (overridable with a `docker-compose.override.yml`), while the
  base compose file builds production-like images for the reviewer.
- **Proxy correctness constraints** (so the reviewer never hits a cookie/CORS
  surprise):
  - Use Next.js `rewrites()` for `/api/*` → `http://backend:8000`, **not** a
    hand-rolled route handler. `rewrites()` forwards method, headers, and the
    request body untouched and passes `Set-Cookie` back unmodified — exactly
    what the login flow needs.
  - Raise the proxy/upload body limit to comfortably exceed the 10 MB resume
    cap, so a large-but-legal file isn't rejected at the proxy layer *before*
    FastAPI's own validation can return a clean `413`.
  - Only port `3000` is required for the reviewer; `8000`/`9001` are optional
    debug conveniences. Nothing in the browser path should ever reference
    `:8000` directly.

## 14. Production Deployment Considerations

Deliberately *described, not built* — the take-home runs locally, but the
design shouldn't paint anyone into a corner:

- **SQLite → PostgreSQL**: change `DATABASE_URL`; SQLAlchemy + Alembic + the
  portable schema (§6) make this a config change. Managed Postgres
  (RDS/Cloud SQL) is the obvious target.
- **MinIO → AWS S3**: change `S3_ENDPOINT_URL`/credentials (drop the endpoint
  override); `boto3` and pre-signed URLs are provider-agnostic. Delete the
  MinIO services from the deployment.
- **Resend**: unchanged — it is already an external managed API; just a
  production API key and a verified sending domain.
- **Frontend/backend hosting**: the Next.js app and FastAPI service are
  stateless (state lives in DB + object storage), so they deploy anywhere
  containers run (ECS, Cloud Run, Fly.io, a VM behind nginx). HTTPS
  terminates at the LB; set `Secure` cookies and tighten CORS to the real
  domain.
- **Auth hardening path** (if ever needed): shorter token lifetimes + refresh
  tokens, token revocation list, SSO/OIDC for attorneys, MFA. The single
  `attorneys` table and isolated `AuthService` keep this an additive change.
- **Email reliability path**: adopt the transactional outbox described in §9
  (email rows written atomically with the lead, drained by a worker), then
  scale the worker with Celery + Redis or SQS if volume grows. This closes
  the "lead saved, email lost" gap without changing the submission API.
- **Observability**: structured JSON logs are already there; production adds
  request-id tracing and error reporting (Sentry).

## 15. Trade-offs & Technology Rationale

**FastAPI** — modern, async, typed; Pydantic gives validation and OpenAPI
docs for free; the dependency-injection system makes auth and adapter
swapping clean. A natural fit for a small, well-typed API.

**Next.js** — the assignment mandates it. App Router gives us server
components (attorney pages can check auth server-side and redirect before
rendering), middleware for route protection, and first-class DX.

**SQLite — and why it's acceptable here:**

- The workload is tiny and low-concurrency: a handful of attorneys reading
  lists, plus occasional single-row inserts. SQLite handles thousands of such
  reads per second without breaking a sweat.
- **Zero operational surface**: no server to run, back up, or secure; the DB
  is one file on a volume — ideal for a reviewer running `docker compose up`
  on a laptop.
- Its known limitation — **one writer at a time** — doesn't bite: lead
  submissions are serialized single inserts, and attorney updates are rare.
  WAL mode further reduces read/write contention.
- The *only* real production concerns (write concurrency, network access from
  multiple app instances, replication/HA tooling) are addressed by design:
  SQLAlchemy + Alembic + env-configured `DATABASE_URL` make PostgreSQL a
  drop-in upgrade the day those concerns become real. Choosing SQLite here is
  not ignorance of PostgreSQL's merits — it's right-sizing the infrastructure
  to the actual load while keeping the exit ramp paved.

**MinIO** — lets us write production-shaped S3 code (boto3, pre-signed URLs,
bucket semantics) against a local container, with the AWS migration being
purely configuration. Storing resumes as objects (§7) instead of DB blobs
keeps the database small and fast, avoids large-binary read/write contention
in SQLite, enables direct browser-to-storage downloads via signed URLs, and
makes any future DB migration trivially small.

**Resend** — a managed transactional-email API: no SMTP server to run, good
deliverability, simple SDK, free tier covers a demo. Fits the "external
provider" requirement and stays put in production.

**JWT in HttpOnly cookie** — stateless verification (no session table, §8),
XSS-resistant storage, CSRF mitigated by `SameSite=Lax`. Trade-off accepted:
no pre-expiry revocation.

**What was deliberately left out** (to keep the take-home honest):
background job queues, rate limiting, refresh tokens, multi-role RBAC,
Kubernetes, Terraform. Each has a documented upgrade path above; none is
needed to demonstrate the system working correctly.

---

## Assumptions

- A single attorney role; attorneys are seeded, not self-service. The seed
  reads `ADMIN_EMAIL` / `ADMIN_PASSWORD` from env (`.env.example` defaults
  them to `admin@tryalma.com` / `password`).
- One shared notification inbox for new-lead emails (`ATTORNEY_NOTIFY_EMAIL`),
  not per-attorney routing.
- Resume formats restricted to `.pdf`, `.doc`, `.docx`, ≤ 10 MB.
- Lead state moves between `PENDING` and `REACHED_OUT`; duplicate applications
  from the same email are allowed.
- The reviewer has (or will create) a free Resend account + API key; without
  one, submission still works and email failures are logged.
- The browser reaches the app only through Next.js on `:3000`; all API calls
  are same-origin and proxied server-side to FastAPI (no cross-origin cookie
  or CORS-credentials setup). This resolves the cookie-origin concern: the
  JWT cookie is first-party on the frontend origin, readable by Next.js
  middleware and forwarded to FastAPI by the proxy.
