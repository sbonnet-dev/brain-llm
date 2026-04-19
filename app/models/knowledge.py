"""Knowledge ORM model.

A knowledge base is a set of documents/URLs/text that can be attached to
agents or teams so they can retrieve information from it.
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Knowledge(Base):
    """A knowledge base definition."""

    __tablename__ = "knowledges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Supported sources: "url", "pdf", "text", "markdown", "website".
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)

    # List of URLs or file paths to ingest.
    sources: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Optional embedder configuration (provider id, embedding model, ...).
    embedder: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Vector database configuration, e.g. {"type": "lancedb", "uri": "..."}.
    vector_db: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
