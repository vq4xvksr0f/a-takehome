"""API error helpers and handlers.

All error responses use the envelope `{ "detail": str, "code": str }`.
`api_error` raises an ApiError (a plain Exception, not FastAPI's HTTPException)
so that every error response — including 401/404/409 raised from routers —
flows through the registered handler and gets the envelope shape; FastAPI's
built-in HTTPException handler does not add a `code` field.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str, code: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.code = code


def api_error(status_code: int, detail: str, code: str) -> ApiError:
    return ApiError(status_code, detail, code)


def unauthorized(detail: str = "Not authenticated") -> ApiError:
    return api_error(status.HTTP_401_UNAUTHORIZED, detail, "UNAUTHORIZED")


def not_found(detail: str = "Resource not found") -> ApiError:
    return api_error(status.HTTP_404_NOT_FOUND, detail, "NOT_FOUND")


def conflict(detail: str) -> ApiError:
    return api_error(status.HTTP_409_CONFLICT, detail, "CONFLICT")


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "code": "VALIDATION_ERROR",
            "errors": exc.errors(),
        },
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "code": "INTERNAL_ERROR"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
