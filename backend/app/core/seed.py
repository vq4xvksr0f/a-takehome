"""Idempotent admin seed: ensure the ADMIN_EMAIL attorney exists."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Attorney
from .config import Settings
from .security import hash_password

logger = logging.getLogger(__name__)


def seed_admin(db: Session, settings: Settings) -> None:
    existing = db.scalar(
        select(Attorney).where(Attorney.email == settings.ADMIN_EMAIL)
    )
    if existing is not None:
        logger.info("Admin attorney %s already exists; skipping seed", settings.ADMIN_EMAIL)
        return
    db.add(
        Attorney(
            email=settings.ADMIN_EMAIL,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
        )
    )
    db.commit()
    logger.info("Seeded admin attorney %s", settings.ADMIN_EMAIL)
