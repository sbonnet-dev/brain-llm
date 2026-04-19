"""Tool ORM model.

A tool is a capability that can be attached to an agent or a team, e.g.
a built-in Agno tool (DuckDuckGo, Yahoo Finance, ...) or a custom function
described by a JSON schema.
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Tool(Base):
    """A tool definition that can be referenced by agents or teams."""

    __tablename__ = "tools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)

    # "builtin" references an Agno tool class, "custom" describes a callable.
    kind: Mapped[str] = mapped_column(String(32), nullable=False)

    # For "builtin": the Agno class name (e.g. "DuckDuckGoTools").
    # For "custom":  an identifier your runtime can resolve to a function.
    reference: Mapped[str] = mapped_column(String(256), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
