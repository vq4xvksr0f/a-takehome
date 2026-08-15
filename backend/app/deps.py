"""Backwards-compatible re-export of the dependency providers.

These moved to `app.api.deps` in the layered restructure. This shim keeps
existing imports (`from app.deps import ...`) working without duplicating any
logic. New code should import from `app.api.deps` directly.
"""

from .api.deps import (  # noqa: F401
    TOKEN_COOKIE,
    get_current_attorney,
    get_db,
    get_email_client,
    get_object_store,
)
