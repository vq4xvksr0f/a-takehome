"""API tests: TestClient + temp SQLite + fake ObjectStore/EmailClient.

The storage and email adapters are dependency-overridden so tests need no
MinIO or network. A fresh temp-file SQLite DB (and dependency overrides) is
used per test, and migrations + seed run once per session against that file.
"""

import io
import os
import tempfile
import uuid

import pytest
from fastapi.testclient import TestClient

# Unique temp DB per test module run; migrations+seed run against it below.
_DB_FD, _DB_PATH = tempfile.mkstemp(suffix=".db")
os.close(_DB_FD)
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("ADMIN_EMAIL", "admin@tryalma.com")
os.environ.setdefault("ADMIN_PASSWORD", "password")
os.environ.setdefault("ATTORNEY_NOTIFY_EMAIL", "attorney@tryalma.com")

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.api.deps import get_email_client, get_object_store  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.core.seed import seed_admin  # noqa: E402
from app.main import app, run_migrations  # noqa: E402


class FakeObjectStore:
    """In-memory stand-in for MinIO/S3."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, fileobj, key: str, content_type: str) -> None:
        self.objects[key] = fileobj.read()

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)

    def presigned_get_url(self, key: str, expires: int) -> str:
        return f"http://fake-s3.local/{key}?expires={expires}"


class SpyEmailClient:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    def send(self, to: str, subject: str, html: str) -> None:
        self.sent.append({"to": to, "subject": subject, "html": html})


fake_store = FakeObjectStore()
spy_email = SpyEmailClient()


@pytest.fixture(autouse=True, scope="session")
def _migrate_and_seed() -> None:
    run_migrations()
    with SessionLocal() as db:
        seed_admin(db, get_settings())


@pytest.fixture()
def client() -> TestClient:
    app.dependency_overrides[get_object_store] = lambda: fake_store
    app.dependency_overrides[get_email_client] = lambda: spy_email
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Helpers ──────────────────────────────────────────────────────────────


def _submit_lead(client: TestClient, **overrides) -> object:
    payload = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": f"ada-{uuid.uuid4().hex[:8]}@example.com",
    }
    payload.update(overrides.pop("data", {}))
    files = overrides.pop(
        "files",
        {"resume": ("resume.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
    )
    return client.post("/api/leads", data=payload, files=files, **overrides)


def _login(client: TestClient) -> TestClient:
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@tryalma.com", "password": "password"},
    )
    assert resp.status_code == 200, resp.text
    return client


# ── Tests ────────────────────────────────────────────────────────────────


def test_health_is_public(client: TestClient) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_submit_lead_success_persists_and_emails(client: TestClient) -> None:
    resp = _submit_lead(client)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["first_name"] == "Ada"
    assert body["state"] == "PENDING"
    assert body["resume_filename"] == "resume.pdf"
    assert "resume_object_key" not in body  # not leaked in public response
    # The object was stored.
    assert len(fake_store.objects) == 1
    key = next(iter(fake_store.objects))
    assert key.startswith("resumes/") and key.endswith(".pdf")
    # Both emails were sent (prospect + attorney notification).
    recipients = {m["to"] for m in spy_email.sent}
    assert body["email"] in recipients
    assert "attorney@tryalma.com" in recipients


def test_lead_list_and_detail_require_auth(client: TestClient) -> None:
    _submit_lead(client)
    assert client.get("/api/leads").status_code == 401
    lead_id = _submit_lead(client).json()["id"]
    assert client.get(f"/api/leads/{lead_id}").status_code == 401
    assert client.get(f"/api/leads/{lead_id}/resume").status_code == 401
    assert (
        client.patch(f"/api/leads/{lead_id}", json={"state": "REACHED_OUT"}).status_code
        == 401
    )


def test_login_sets_cookie_and_authed_list_works(client: TestClient) -> None:
    _submit_lead(client)
    _login(client)
    assert "alma_token" in client.cookies
    resp = client.get("/api/leads")
    assert resp.status_code == 200
    leads = resp.json()
    assert len(leads) >= 1
    assert {"id", "first_name", "last_name", "email", "state", "created_at"} <= set(
        leads[0]
    )
    # Detail endpoint works too.
    detail = client.get(f"/api/leads/{leads[0]['id']}")
    assert detail.status_code == 200
    assert detail.json()["resume_filename"] == "resume.pdf"


def test_login_bad_credentials_is_generic_401(client: TestClient) -> None:
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@tryalma.com", "password": "wrong"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHORIZED"
    resp = client.post(
        "/api/auth/login",
        json={"email": "nobody@tryalma.com", "password": "password"},
    )
    assert resp.status_code == 401


def test_logout_clears_cookie(client: TestClient) -> None:
    _login(client)
    assert "alma_token" in client.cookies
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 204
    assert client.cookies.get("alma_token") in (None, "")


def test_state_transition_pending_to_reached_out_then_409(client: TestClient) -> None:
    lead_id = _submit_lead(client).json()["id"]
    _login(client)

    resp = client.patch(f"/api/leads/{lead_id}", json={"state": "REACHED_OUT"})
    assert resp.status_code == 200
    assert resp.json()["state"] == "REACHED_OUT"

    # Second transition attempt is a conflict.
    resp = client.patch(f"/api/leads/{lead_id}", json={"state": "REACHED_OUT"})
    assert resp.status_code == 409
    assert resp.json()["code"] == "CONFLICT"


def test_patch_invalid_state_value_is_409(client: TestClient) -> None:
    lead_id = _submit_lead(client).json()["id"]
    _login(client)
    resp = client.patch(f"/api/leads/{lead_id}", json={"state": "PENDING"})
    assert resp.status_code == 409


def test_patch_unknown_lead_is_404(client: TestClient) -> None:
    _login(client)
    resp = client.patch(
        f"/api/leads/{uuid.uuid4()}", json={"state": "REACHED_OUT"}
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"


def test_submit_invalid_email_is_422(client: TestClient) -> None:
    resp = _submit_lead(
        client,
        data={"first_name": "Ada", "last_name": "Lovelace", "email": "not-an-email"},
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_submit_bad_extension_is_415(client: TestClient) -> None:
    resp = _submit_lead(
        client,
        files={"resume": ("resume.exe", io.BytesIO(b"MZ"), "application/x-msdownload")},
    )
    assert resp.status_code == 415
    assert resp.json()["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_submit_oversized_file_is_413(client: TestClient) -> None:
    big = io.BytesIO(b"0" * (10 * 1024 * 1024 + 1))
    resp = _submit_lead(
        client,
        files={"resume": ("resume.pdf", big, "application/pdf")},
    )
    assert resp.status_code == 413
    assert resp.json()["code"] == "FILE_TOO_LARGE"


def test_resume_redirects_to_presigned_url(client: TestClient) -> None:
    lead_id = _submit_lead(client).json()["id"]
    _login(client)
    resp = client.get(f"/api/leads/{lead_id}/resume", follow_redirects=False)
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location.startswith("http://fake-s3.local/resumes/")
    assert "expires=60" in location
