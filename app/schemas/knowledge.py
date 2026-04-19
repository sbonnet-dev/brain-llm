"""Pydantic schemas for knowledge bases."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SourceType = Literal["url", "pdf", "text", "markdown", "website"]


class KnowledgeBase(BaseModel):
    """Shared knowledge fields."""

    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None
    source_type: SourceType
    sources: list[str] | None = None
    embedder: dict[str, Any] | None = None
    vector_db: dict[str, Any] | None = None


class KnowledgeCreate(KnowledgeBase):
    """Payload for creating a knowledge base."""


class KnowledgeUpdate(BaseModel):
    """Payload for updating a knowledge base."""

    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = None
    source_type: SourceType | None = None
    sources: list[str] | None = None
    embedder: dict[str, Any] | None = None
    vector_db: dict[str, Any] | None = None


class KnowledgeRead(KnowledgeBase):
    """Knowledge base as returned by the API."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
