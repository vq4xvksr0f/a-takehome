"""Auth routes: login (sets JWT cookie) and logout (clears it)."""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import Settings, get_settings
from ..core.errors import unauthorized
from ..core.security import create_access_token, verify_password
from ..models import Attorney
from .deps import TOKEN_COOKIE, get_db
from .schemas import AttorneyOut, LoginRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AttorneyOut)
def login(
    body: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Attorney:
    attorney = db.scalar(select(Attorney).where(Attorney.email == body.email))
    if attorney is None or not verify_password(
        body.password, attorney.password_hash
    ):
        # Deliberately generic: don't reveal whether the account exists.
        raise unauthorized("Invalid credentials")

    token = create_access_token(attorney.id, attorney.email)
    response.set_cookie(
        TOKEN_COOKIE,
        token,
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        path="/",
    )
    return attorney


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(TOKEN_COOKIE, path="/")
    return None
