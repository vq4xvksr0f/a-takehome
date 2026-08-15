"""Lead routes: public submission + authenticated attorney views.

HTTP concerns only — parse the request, delegate to LeadService, render the
response. Business logic lives in services/lead_service.py; queries live in
repositories/lead_repository.py; input rules live in validation.py.
"""

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..adapters.email_client import EmailClient
from ..adapters.storage import ObjectStore
from ..core.config import Settings, get_settings
from ..models import Attorney, Lead
from ..repositories.lead_repository import LeadRepository
from ..services.email_service import EmailService
from ..services.lead_service import LeadService
from ..services.validation import validate_email, validate_name
from .deps import (
    get_current_attorney,
    get_db,
    get_email_client,
    get_object_store,
)
from .schemas import (
    LeadCreateResponse,
    LeadDetail,
    LeadStateUpdate,
    LeadSummary,
)

router = APIRouter(prefix="/leads", tags=["leads"])


def get_lead_service(
    db: Session = Depends(get_db),
    object_store: ObjectStore = Depends(get_object_store),
    email_client: EmailClient = Depends(get_email_client),
    settings: Settings = Depends(get_settings),
) -> LeadService:
    """Assemble a LeadService for the request.

    A single dependency (rather than per-handler wiring) gives tests one clean
    override point for the storage/email adapters.
    """
    return LeadService(
        leads=LeadRepository(db),
        object_store=object_store,
        email_service=EmailService(email_client),
        notify_email=settings.ATTORNEY_NOTIFY_EMAIL,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=LeadCreateResponse)
def create_lead(
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    resume: UploadFile = File(...),
    service: LeadService = Depends(get_lead_service),
) -> Lead:
    return service.submit_lead(
        first_name=validate_name(first_name, "first_name"),
        last_name=validate_name(last_name, "last_name"),
        email=validate_email(email),
        resume_fileobj=resume.file,
        resume_filename=resume.filename,
        resume_content_type=resume.content_type,
    )


@router.get("", response_model=list[LeadSummary])
def list_leads(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: LeadService = Depends(get_lead_service),
    _: Attorney = Depends(get_current_attorney),
) -> list[Lead]:
    return service.list_leads(limit, offset)


@router.get("/{lead_id}", response_model=LeadDetail)
def get_lead(
    lead_id: str,
    service: LeadService = Depends(get_lead_service),
    _: Attorney = Depends(get_current_attorney),
) -> Lead:
    return service.get_lead(lead_id)


@router.get("/{lead_id}/resume")
def get_lead_resume(
    lead_id: str,
    service: LeadService = Depends(get_lead_service),
    _: Attorney = Depends(get_current_attorney),
) -> RedirectResponse:
    url = service.get_resume_download_url(lead_id)
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


@router.patch("/{lead_id}", response_model=LeadDetail)
def update_lead_state(
    lead_id: str,
    body: LeadStateUpdate,
    service: LeadService = Depends(get_lead_service),
    _: Attorney = Depends(get_current_attorney),
) -> Lead:
    return service.update_state(lead_id, body.state)
