"""Lead business logic: submission orchestration and the state machine.

This layer coordinates the repository, object store, and email service, and
owns the domain rules (design doc §3/§5). It has no FastAPI or SQLAlchemy
imports — those live in the api/ and repositories/ layers respectively.
"""

import io
import logging
import uuid

from ..adapters.storage import ObjectStore
from ..core.errors import conflict, not_found
from ..models import Lead
from ..repositories.lead_repository import LeadRepository
from .email_service import EmailService
from .validation import read_resume_within_cap, resume_extension

logger = logging.getLogger(__name__)

RESUME_URL_EXPIRES_SECONDS = 60


class LeadService:
    def __init__(
        self,
        leads: LeadRepository,
        object_store: ObjectStore,
        email_service: EmailService,
        notify_email: str,
    ) -> None:
        self._leads = leads
        self._object_store = object_store
        self._email_service = email_service
        self._notify_email = notify_email

    def submit_lead(
        self,
        first_name: str,
        last_name: str,
        email: str,
        resume_fileobj,
        resume_filename: str | None,
        resume_content_type: str | None,
    ) -> Lead:
        """Persist the resume and lead, then fire the notification emails.

        Order matters: upload the object first, then insert the row; if the
        insert fails, best-effort delete the orphaned object (§3). Emails send
        after commit and never fail the request (§11).
        """
        ext = resume_extension(resume_filename)
        data = read_resume_within_cap(resume_fileobj)

        object_key = f"resumes/{uuid.uuid4()}{ext}"
        self._object_store.put(
            io.BytesIO(data),
            object_key,
            resume_content_type or "application/octet-stream",
        )

        lead = Lead(
            first_name=first_name,
            last_name=last_name,
            email=email,
            state="PENDING",
            resume_object_key=object_key,
            resume_filename=resume_filename or f"resume{ext}",
        )
        try:
            lead = self._leads.add(lead)
        except Exception:
            try:
                self._object_store.delete(object_key)
            except Exception:
                logger.exception("Failed to delete orphan object %s", object_key)
            raise

        logger.info("lead created id=%s email=%s", lead.id, lead.email)
        self._email_service.send_submission_emails(lead, self._notify_email)
        return lead

    def list_leads(self, limit: int, offset: int) -> list[Lead]:
        return list(self._leads.list(limit, offset))

    def get_lead(self, lead_id: str) -> Lead:
        lead = self._leads.get(lead_id)
        if lead is None:
            raise not_found("Lead not found")
        return lead

    def get_resume_download_url(self, lead_id: str) -> str:
        lead = self.get_lead(lead_id)
        return self._object_store.presigned_get_url(
            lead.resume_object_key, expires=RESUME_URL_EXPIRES_SECONDS
        )

    def update_state(self, lead_id: str, new_state: str) -> Lead:
        """Transition a lead between PENDING and REACHED_OUT (§5).

        The state machine allows a lead to move between the two states in
        either direction. Only the two known states are legal, and a no-op
        "transition" to the current state is a 409 like any other illegal value.
        """
        lead = self.get_lead(lead_id)
        if new_state not in ("PENDING", "REACHED_OUT"):
            raise conflict(
                f'Cannot transition lead to {new_state!r}; state must be "PENDING" or "REACHED_OUT"'
            )
        if new_state == lead.state:
            raise conflict(f"Lead is already {lead.state}")
        previous = lead.state
        lead.state = new_state
        updated = self._leads.save(lead)
        logger.info("lead %s transitioned %s -> %s", lead.id, previous, new_state)
        return updated
