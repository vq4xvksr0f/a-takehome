"""Persistence operations for the Lead aggregate.

This is the only module that runs Lead queries. Services call these methods;
they never construct SQLAlchemy statements themselves.
"""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import Lead, LeadActivity


class LeadRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, lead: Lead) -> Lead:
        """Insert and commit a new lead, returning it with DB defaults applied.

        Raises on failure; the caller is responsible for any compensating
        action (e.g. deleting an already-uploaded resume object).
        """
        self._db.add(lead)
        self._db.commit()
        self._db.refresh(lead)
        return lead

    def get(self, lead_id: str) -> Lead | None:
        # Eagerly load activities (and their attorneys) so the detail response
        # can render the audit trail without extra queries.
        stmt = select(Lead).where(Lead.id == lead_id).options(
            selectinload(Lead.activities).selectinload(LeadActivity.attorney)
        )
        return self._db.scalars(stmt).first()

    def list(self, limit: int, offset: int) -> Sequence[Lead]:
        """Newest-first page of leads."""
        stmt = select(Lead).order_by(Lead.created_at.desc()).limit(limit).offset(offset)
        return self._db.scalars(stmt).all()

    def save(self, lead: Lead) -> Lead:
        """Commit in-place changes to an existing lead."""
        self._db.commit()
        self._db.refresh(lead)
        return lead

    def save_state_change(
        self, lead: Lead, activity: LeadActivity
    ) -> Lead:
        """Commit a state change and its audit row in one transaction."""
        self._db.add(activity)
        self._db.commit()
        self._db.refresh(lead)
        return lead
