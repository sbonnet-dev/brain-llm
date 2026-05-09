"""Model ORM definition.

A Model represents a concrete inference endpoint exposed by a provider,
e.g. ``llama3.2:latest`` (llm) or ``nomic-embed-text`` (embedder).
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Model(Base):
    """An AI model exposed by a provider."""

    __tablename__ = "models"
    __table_args__ = (
        UniqueConstraint("provider_id", "name", name="uq_models_provider_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identifier used by the provider, e.g. "llama3.2:latest".
    name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)

    # Supported model types: "llm", "vlm", "embedder", "reranker", "audio".
    model_type: Mapped[str] = mapped_column(String(32), nullable=False)

    provider_id: Mapped[int] = mapped_column(
        ForeignKey("providers.id", ondelete="CASCADE"), nullable=False
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
