"""Pydantic schemas for tools."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ToolKind = Literal["builtin", "custom", "python_file"]


class ToolBase(BaseModel):
    """Shared tool fields."""

    name: str = Field(..., min_length=1, max_length=128)
    kind: ToolKind
    reference: str = Field(..., min_length=1, max_length=256)
    description: str | None = None
    dependencies: str | None = Field(
        None,
        max_length=1024,
        description="Comma-separated pip packages to install (e.g. 'yfinance,duckduckgo-search').",
    )


class ToolCreate(ToolBase):
    """Payload for creating a tool."""


class ToolUpdate(BaseModel):
    """Payload for updating a tool."""

    name: str | None = Field(None, min_length=1, max_length=128)
    kind: ToolKind | None = None
    reference: str | None = None
    description: str | None = None
    dependencies: str | None = Field(None, max_length=1024)


class ToolRead(ToolBase):
    """Tool as returned by the API."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
