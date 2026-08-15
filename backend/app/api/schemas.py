"""Pydantic request/response schemas for the API."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ── Leads ──────────────────────────────────────────────────────────────


class LeadSummary(BaseModel):
    """Fields returned in the paginated list view."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    first_name: str
    last_name: str
    email: str
    state: str
    created_at: str


class LeadDetail(LeadSummary):
    """Full lead record, including resume metadata and update time."""

    resume_filename: str
    updated_at: str


class LeadCreateResponse(LeadDetail):
    """201 response body for POST /api/leads (the lead's public fields)."""


class LeadStateUpdate(BaseModel):
    state: str = Field(..., description='Target state: "PENDING" or "REACHED_OUT".')


class _EmailCheck(BaseModel):
    """Internal helper for validating the multipart email form field."""

    email: EmailStr


# ── Auth ───────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AttorneyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    created_at: str
