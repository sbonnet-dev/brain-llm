"""Custom exceptions and FastAPI error handlers."""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class BrainLLMError(Exception):
    """Base exception for all application-specific errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "internal_error"

    def __init__(self, message: str, details: Any | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(BrainLLMError):
    """Raised when a requested resource does not exist."""

    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ValidationError(BrainLLMError):
    """Raised when input validation fails in a service layer."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "validation_error"


class ConflictError(BrainLLMError):
    """Raised when an operation conflicts with the current state."""

    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class ProviderError(BrainLLMError):
    """Raised when an LLM provider cannot be reached or is misconfigured."""

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "provider_error"


def _error_payload(code: str, message: str, details: Any | None = None) -> dict:
    """Build the JSON envelope returned for every error response."""
    payload: dict = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    return payload


def register_exception_handlers(app: FastAPI) -> None:
    """Attach application-wide exception handlers to the FastAPI app."""

    @app.exception_handler(BrainLLMError)
    async def _handle_app_error(_: Request, exc: BrainLLMError) -> JSONResponse:
        logger.warning("Application error: %s - %s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        logger.info("Request validation error: %s", exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_payload("validation_error", "Invalid request", exc.errors()),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_payload("internal_error", "An unexpected error occurred"),
        )
