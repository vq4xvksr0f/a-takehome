"""ORM models. Mirrors docs/system-design.md §6.

Timestamps are ISO-8601 UTC strings (TEXT) for SQLite/PostgreSQL portability.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .core.db import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=new_uuid)
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False, default="PENDING")
    resume_object_key: Mapped[str] = mapped_column(Text, nullable=False)
    resume_filename: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utc_now_iso)
    updated_at: Mapped[str] = mapped_column(
        Text, nullable=False, default=utc_now_iso, onupdate=utc_now_iso
    )

    activities: Mapped[list["LeadActivity"]] = relationship(
        back_populates="lead", order_by="LeadActivity.created_at.desc()"
    )

    __table_args__ = (
        CheckConstraint("state IN ('PENDING', 'REACHED_OUT')", name="ck_leads_state"),
        Index("idx_leads_created_at", created_at.desc()),
        Index("idx_leads_state", state),
    )


class Attorney(Base):
    __tablename__ = "attorneys"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utc_now_iso)


class LeadActivity(Base):
    """Audit trail of lead state transitions: who moved what, from/to, when."""

    __tablename__ = "lead_activities"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=new_uuid)
    lead_id: Mapped[str] = mapped_column(
        Text, ForeignKey("leads.id"), nullable=False
    )
    attorney_id: Mapped[str] = mapped_column(
        Text, ForeignKey("attorneys.id"), nullable=False
    )
    from_state: Mapped[str] = mapped_column(Text, nullable=False)
    to_state: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utc_now_iso)

    lead: Mapped[Lead] = relationship(back_populates="activities")
    attorney: Mapped["Attorney"] = relationship()

    __table_args__ = (
        CheckConstraint(
            "from_state IN ('PENDING', 'REACHED_OUT')", name="ck_activity_from_state"
        ),
        CheckConstraint(
            "to_state IN ('PENDING', 'REACHED_OUT')", name="ck_activity_to_state"
        ),
        Index("idx_activity_lead_id", lead_id),
    )


class EmailOutbox(Base):
    """Transactional outbox (design doc §9): schema only — no worker is built."""

    __tablename__ = "email_outbox"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=new_uuid)
    lead_id: Mapped[str] = mapped_column(Text, ForeignKey("leads.id"), nullable=False)
    recipient: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    html: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utc_now_iso)

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'sent', 'failed')", name="ck_outbox_status"),
    )
