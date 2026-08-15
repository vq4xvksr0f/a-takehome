"""Application settings, read from environment variables.

The variable names match the root `.env.example` exactly — that file is the
source of truth for the configuration contract.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


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
