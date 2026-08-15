"""Password hashing (bcrypt) and JWT creation/verification (HS256)."""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from .config import get_settings

ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(attorney_id: str, email: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    claims = {
        "sub": attorney_id,
        "email": email,
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and verify a token. Raises jwt.PyJWTError on any failure."""
    settings = get_settings()
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
