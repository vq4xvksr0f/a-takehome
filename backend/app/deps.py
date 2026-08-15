"""Shared FastAPI dependencies: DB session, adapters, and JWT auth."""

from collections.abc import Generator

import jwt
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .db import SessionLocal
from .email_client import EmailClient, build_email_client
from .errors import unauthorized
from .models import Attorney
from .security import decode_access_token
from .storage import BotoObjectStore, ObjectStore

TOKEN_COOKIE = "alma_token"

# Adapters are stateless and thread-safe enough to share across requests.
_object_store: ObjectStore | None = None
_email_client: EmailClient | None = None


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_object_store() -> ObjectStore:
    global _object_store
    if _object_store is None:
        _object_store = BotoObjectStore()
    return _object_store


def get_email_client(settings: Settings = Depends(get_settings)) -> EmailClient:
    global _email_client
    if _email_client is None:
        _email_client = build_email_client(settings)
    return _email_client


def get_current_attorney(
    request: Request, db: Session = Depends(get_db)
) -> Attorney:
    """Require a valid `alma_token` JWT cookie; 401 on any failure."""
    token = request.cookies.get(TOKEN_COOKIE)
    if not token:
        raise unauthorized("Not authenticated")
    try:
        claims = decode_access_token(token)
    except jwt.PyJWTError:
        raise unauthorized("Invalid or expired token")
    attorney_id = claims.get("sub")
    if not attorney_id:
        raise unauthorized("Invalid or expired token")
    attorney = db.get(Attorney, attorney_id)
    if attorney is None:
        raise unauthorized("Invalid or expired token")
    return attorney
