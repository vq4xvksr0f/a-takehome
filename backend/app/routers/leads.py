"""Lead routes: public submission + authenticated attorney views."""

import io
import logging
import os
import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import (
    get_current_attorney,
    get_db,
    get_email_client,
    get_object_store,
)
from ..email_client import (
    EmailClient,
    attorney_notification_html,
    prospect_confirmation_html,
)
from ..errors import api_error, conflict, not_found
from ..models import Attorney, Lead
from ..schemas import (
    LeadCreateResponse,
    LeadDetail,
    LeadStateUpdate,
    LeadSummary,
    _EmailCheck,
)
from ..storage import ObjectStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leads", tags=["leads"])

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}
MAX_RESUME_BYTES = 10 * 1024 * 1024  # 10 MB
RESUME_URL_EXPIRES_SECONDS = 60
MAX_NAME_LENGTH = 100


def _validate_name(value: str, field: str) -> str:
    name = value.strip()
    if not name or len(name) > MAX_NAME_LENGTH:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"{field} must be 1-{MAX_NAME_LENGTH} characters",
            "VALIDATION_ERROR",
        )
    return name


def _validate_email(email: str) -> str:
    try:
        return _EmailCheck(email=email.strip()).email
    except ValidationError:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Invalid email address",
            "VALIDATION_ERROR",
        )


def _send_submission_emails(
    email_client: EmailClient, lead: Lead, notify_email: str
) -> None:
    """Best-effort post-commit emails: failures are logged, never propagated."""
    try:
        email_client.send(
            to=lead.email,
            subject="We received your application",
            html=prospect_confirmation_html(lead.first_name),
        )
    except Exception:
        logger.exception("Failed to send prospect confirmation for lead %s", lead.id)
    try:
        email_client.send(
            to=notify_email,
            subject="New lead submission",
            html=attorney_notification_html(
                lead.first_name, lead.last_name, lead.email
            ),
        )
    except Exception:
        logger.exception("Failed to send attorney notification for lead %s", lead.id)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=LeadCreateResponse)
def create_lead(
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    resume: UploadFile = File(...),
    db: Session = Depends(get_db),
    object_store: ObjectStore = Depends(get_object_store),
    email_client: EmailClient = Depends(get_email_client),
) -> Lead:
    first_name = _validate_name(first_name, "first_name")
    last_name = _validate_name(last_name, "last_name")
    email = _validate_email(email)

    ext = os.path.splitext(resume.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise api_error(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "Unsupported file type; allowed: .pdf, .doc, .docx",
            "UNSUPPORTED_MEDIA_TYPE",
        )

    # Enforce the 10 MB cap while reading: read at most cap+1 bytes.
    data = resume.file.read(MAX_RESUME_BYTES + 1)
    if len(data) > MAX_RESUME_BYTES:
        raise api_error(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "Resume exceeds the 10 MB limit",
            "FILE_TOO_LARGE",
        )

    object_key = f"resumes/{uuid.uuid4()}{ext}"
    object_store.put(
        io.BytesIO(data),
        object_key,
        resume.content_type or "application/octet-stream",
    )

    lead = Lead(
        first_name=first_name,
        last_name=last_name,
        email=email,
        state="PENDING",
        resume_object_key=object_key,
        resume_filename=resume.filename or f"resume{ext}",
    )
    try:
        db.add(lead)
        db.commit()
    except Exception:
        db.rollback()
        # Best-effort cleanup of the orphaned uploaded object.
        try:
            object_store.delete(object_key)
        except Exception:
            logger.exception("Failed to delete orphan object %s", object_key)
        raise
    db.refresh(lead)

    from ..config import get_settings

    _send_submission_emails(
        email_client, lead, get_settings().ATTORNEY_NOTIFY_EMAIL
    )
    return lead


@router.get("", response_model=list[LeadSummary])
def list_leads(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: Attorney = Depends(get_current_attorney),
) -> list[Lead]:
    return list(
        db.scalars(
            select(Lead).order_by(Lead.created_at.desc()).limit(limit).offset(offset)
        )
    )


@router.get("/{lead_id}", response_model=LeadDetail)
def get_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    _: Attorney = Depends(get_current_attorney),
) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise not_found("Lead not found")
    return lead


@router.get("/{lead_id}/resume")
def get_lead_resume(
    lead_id: str,
    db: Session = Depends(get_db),
    _: Attorney = Depends(get_current_attorney),
    object_store: ObjectStore = Depends(get_object_store),
) -> RedirectResponse:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise not_found("Lead not found")
    url = object_store.presigned_get_url(
        lead.resume_object_key, expires=RESUME_URL_EXPIRES_SECONDS
    )
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


@router.patch("/{lead_id}", response_model=LeadDetail)
def update_lead_state(
    lead_id: str,
    body: LeadStateUpdate,
    db: Session = Depends(get_db),
    _: Attorney = Depends(get_current_attorney),
) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise not_found("Lead not found")
    if body.state != "REACHED_OUT" or lead.state != "PENDING":
        raise conflict(
            f"Cannot transition lead from {lead.state} to {body.state}; "
            "only PENDING -> REACHED_OUT is allowed"
        )
    lead.state = "REACHED_OUT"
    db.commit()
    db.refresh(lead)
    return lead
