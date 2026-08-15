"""Input validation for the public lead-submission form.

Pure functions that return a cleaned value or raise an ApiError with the
correct status code and envelope code (design doc §11). Kept out of the HTTP
layer so the rules are unit-testable and reusable.
"""

import os

from fastapi import status
from pydantic import ValidationError

from ..api.schemas import _EmailCheck
from ..core.errors import api_error

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}
MAX_RESUME_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_NAME_LENGTH = 100


def validate_name(value: str, field: str) -> str:
    name = value.strip()
    if not name or len(name) > MAX_NAME_LENGTH:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"{field} must be 1-{MAX_NAME_LENGTH} characters",
            "VALIDATION_ERROR",
        )
    return name


def validate_email(email: str) -> str:
    try:
        return _EmailCheck(email=email.strip()).email
    except ValidationError:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Invalid email address",
            "VALIDATION_ERROR",
        )


def resume_extension(filename: str | None) -> str:
    """Return the validated lowercase extension, or raise 415."""
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise api_error(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "Unsupported file type; allowed: .pdf, .doc, .docx",
            "UNSUPPORTED_MEDIA_TYPE",
        )
    return ext


def read_resume_within_cap(fileobj, max_bytes: int = MAX_RESUME_BYTES) -> bytes:
    """Read at most max_bytes+1 and raise 413 if the upload exceeds the cap.

    Reading with a hard cap avoids buffering an arbitrarily large file in
    memory just to discover it was too big.
    """
    data = fileobj.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise api_error(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "Resume exceeds the 10 MB limit",
            "FILE_TOO_LARGE",
        )
    return data
