"""Pydantic schemas for knowledge bases and their files."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.model import ModelRead


# ---------------------------------------------------------------------------
# Knowledge Base
# ---------------------------------------------------------------------------


class KnowledgeBase(BaseModel):
    """Shared knowledge-base fields."""

    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None
    collection_name: str | None = Field(
        None,
        description="Qdrant collection name. Defaults to 'kb_{id}' if omitted.",
        max_length=128,
    )
    embedder_model_id: int | None = Field(
        None,
        description=(
            "Id of the Model row (model_type='embedder') used to vectorize "
            "documents. Falls back to env defaults when null."
        ),
    )
    vector_db: dict[str, Any] | None = Field(
        None,
        description='Vector store override, e.g. {"type": "qdrant", "url": "http://qdrant:6333"}.',
    )


class KnowledgeCreate(KnowledgeBase):
    """Payload for creating a knowledge base."""


class KnowledgeUpdate(BaseModel):
    """Payload for updating a knowledge base."""

    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = None
    collection_name: str | None = Field(None, max_length=128)
    embedder_model_id: int | None = None
    vector_db: dict[str, Any] | None = None


class KnowledgeRead(KnowledgeBase):
    """Knowledge base as returned by the API."""

    id: int
    status_id: int
    embedder_model: ModelRead | None = Field(
        None,
        description="Embedded snapshot of the linked embedder Model (provider, name, extra_config).",
    )
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Knowledge Files
# ---------------------------------------------------------------------------


class KnowledgeFileRead(BaseModel):
    """File metadata returned by the API."""

    id: int
    knowledge_id: int
    filename: str
    mime_type: str | None = None
    size_bytes: int
    status_id: int
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgeFileContentUpdate(BaseModel):
    """Payload for replacing a file's textual content in place."""

    content: str = Field(..., description="New textual content for the file.")
    mime_type: str | None = Field(None, description="Optional override for the MIME type.")


class KnowledgeFileContent(BaseModel):
    """Textual content of a file."""

    id: int
    filename: str
    mime_type: str | None = None
    content: str


# ---------------------------------------------------------------------------
# Status types & ingestion
# ---------------------------------------------------------------------------


class KnowledgeStatusType(BaseModel):
    """A status code used by knowledge bases and files."""

    id: int
    name: str


class IngestionResult(BaseModel):
    """Outcome of an ingestion run."""

    knowledge_id: int
    file_id: int | None = None
    status_id: int
    files_processed: int = 0
    files_failed: int = 0
    message: str | None = None
