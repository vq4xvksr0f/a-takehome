"""FastAPI application factory: routers, CORS, error handlers, startup."""

import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from alembic.config import Config as AlembicConfig
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from alembic import command as alembic_command

from .api import auth, health, leads
from .core.config import get_settings
from .core.db import SessionLocal
from .core.errors import register_exception_handlers
from .core.seed import seed_admin

_ALEMBIC_INI = str(Path(__file__).resolve().parent.parent / "alembic.ini")

request_logger = logging.getLogger("app.requests")


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

    @app.middleware("http")
    async def log_request_duration(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        request_logger.info(
            "%s %s %s %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

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
