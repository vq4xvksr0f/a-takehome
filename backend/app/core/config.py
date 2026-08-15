"""Application settings, read from environment variables.

The variable names match the root `.env.example` exactly — that file is the
source of truth for the configuration contract.

Also hosts UtcIsoFormatter, the logging formatter log_config.json points at.
It lives here (rather than a one-class module) because this module is imported
early, has no heavy deps, and is safe for dictConfig to import by dotted path.
"""

import logging
from datetime import UTC, datetime
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class UtcIsoFormatter(logging.Formatter):
    """Render log timestamps as ISO-8601 UTC with a trailing 'Z'.

    Containers run in UTC, and a naive timestamp doesn't say so — this makes
    the timezone explicit (e.g. 2026-08-15T03:37:14.809Z).
    """

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        dt = datetime.fromtimestamp(record.created, tz=UTC)
        return dt.strftime("%Y-%m-%dT%H:%M:%S") + f".{int(record.msecs):03d}Z"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Core ──────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:////data/leads.db"
    JWT_SECRET_KEY: str = "dev-secret-change-me"
    JWT_EXPIRE_MINUTES: int = 480  # 8 hours, in minutes
    COOKIE_SECURE: bool = False

    # ── Admin seed ────────────────────────────────────────────────────
    ADMIN_EMAIL: str = "admin@tryalma.com"
    ADMIN_PASSWORD: str = "password"
    EXTRA_ADMIN_EMAILS: str = ""  # comma-separated, seeded with ADMIN_PASSWORD

    @property
    def admin_emails(self) -> list[str]:
        emails = [self.ADMIN_EMAIL]
        emails.extend(e.strip() for e in self.EXTRA_ADMIN_EMAILS.split(",") if e.strip())
        return emails

    # ── Email ─────────────────────────────────────────────────────────
    EMAIL_PROVIDER: Literal["console", "resend"] = "console"
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "Leads <onboarding@resend.dev>"
    ATTORNEY_NOTIFY_EMAIL: str = "attorney@tryalma.com"

    # ── S3 / MinIO ────────────────────────────────────────────────────
    S3_ENDPOINT_URL: str = "http://minio:9000"
    S3_PUBLIC_ENDPOINT: str = "http://localhost:9000"
    S3_BUCKET: str = "resumes"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_REGION: str = "us-east-1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
