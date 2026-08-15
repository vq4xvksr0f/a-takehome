"""Idempotent admin seed: ensure the ADMIN_EMAIL attorney exists."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Attorney
from .config import Settings
from .security import hash_password

logger = logging.getLogger(__name__)


def seed_admin(db: Session, settings: Settings) -> None:
    for email in settings.admin_emails:
        existing = db.scalar(select(Attorney).where(Attorney.email == email))
        if existing is not None:
            logger.info("Admin attorney %s already exists; skipping seed", email)
            continue
        db.add(
            Attorney(
                email=email,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
            )
        )
        logger.info("Seeded admin attorney %s", email)
    db.commit()
