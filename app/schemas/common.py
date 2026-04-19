"""Common response schemas shared by all endpoints."""

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Description of an error returned by the API."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Any | None = Field(None, description="Optional extra information")


class ErrorResponse(BaseModel):
    """Envelope used for every error response."""

    error: ErrorDetail


class DeleteResponse(BaseModel):
    """Response returned after a successful deletion."""

    id: int
    deleted: bool = True
