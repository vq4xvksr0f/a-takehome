"""FastAPI application factory: routers, CORS, error handlers, startup."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import auth, health, leads
from .core.config import get_settings
from .core.db import SessionLocal
from .core.errors import register_exception_handlers
from .core.seed import seed_admin

logger = logging.getLogger(__name__)

_ALEMBIC_INI = str(Path(__file__).resolve().parent.parent / "alembic.ini")


def run_migrations() -> None:
    """Apply Alembic migrations programmatically (alembic upgrade head)."""
    cfg = AlembicConfig(_ALEMBIC_INI)
    alembic_command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    run_migrations()
    with SessionLocal() as db:
        seed_admin(db, settings)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Lead Management API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3300"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(leads.router, prefix="/api")

    return app


app = create_app()
