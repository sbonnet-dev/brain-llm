"""Team ORM model."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Team(Base):
    """A team of agents that cooperate on a task."""

    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Agno team "mode": "coordinate", "route", "collaborate".
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="coordinate")

    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Leader model used by the team coordinator.
    model_id: Mapped[int | None] = mapped_column(
        ForeignKey("models.id", ondelete="SET NULL"), nullable=True
    )

    member_agent_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    tool_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    knowledge_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    extra_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
