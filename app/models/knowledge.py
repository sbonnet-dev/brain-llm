"""Knowledge ORM models.

A KnowledgeBase is a set of files that can be vectorized in Qdrant and
attached to agents or teams. Each KnowledgeBase owns one or more
KnowledgeFiles, which are the raw documents backing it.
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# Status ids match the spec exposed by /knowledge/status-types.
STATUS_NOT_PROCESSED = 1
STATUS_PENDING = 2
STATUS_PROCESSING = 3
STATUS_PROCESSED = 4
STATUS_FAILED = 5

STATUS_TYPES: list[dict] = [
    {"id": STATUS_NOT_PROCESSED, "name": "not-processed"},
    {"id": STATUS_PENDING, "name": "pending"},
    {"id": STATUS_PROCESSING, "name": "processing"},
    {"id": STATUS_PROCESSED, "name": "processed"},
    {"id": STATUS_FAILED, "name": "failed"},
]


class Knowledge(Base):
    """A knowledge base aggregating files indexed in a vector store."""

    __tablename__ = "knowledges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Qdrant collection name — defaults to `kb_{id}` at creation time.
    collection_name: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Optional embedder config: {"provider": "ollama", "model": "nomic-embed-text", ...}
    embedder: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Vector DB overrides: {"type": "qdrant", "url": "...", "api_key": "..."}
    vector_db: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Last-known ingestion status for the whole KB.
    status_id: Mapped[int] = mapped_column(
        Integer, nullable=False, default=STATUS_NOT_PROCESSED
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    files: Mapped[list["KnowledgeFile"]] = relationship(
        "KnowledgeFile",
        back_populates="knowledge",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class KnowledgeFile(Base):
    """A single file stored in a knowledge base."""

    __tablename__ = "knowledge_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    knowledge_id: Mapped[int] = mapped_column(
        ForeignKey("knowledges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Path on disk where the raw file is stored.
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)

    status_id: Mapped[int] = mapped_column(
        Integer, nullable=False, default=STATUS_NOT_PROCESSED
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    knowledge: Mapped["Knowledge"] = relationship("Knowledge", back_populates="files")
