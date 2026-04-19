"""Pydantic schemas for agents."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentBase(BaseModel):
    """Shared agent fields."""

    name: str = Field(..., min_length=1, max_length=128)
    role: str | None = None
    description: str | None = None
    instructions: str | None = None
    model_id: int
    tool_ids: list[int] | None = None
    knowledge_ids: list[int] | None = None
    extra_config: dict[str, Any] | None = None


class AgentCreate(AgentBase):
    """Payload for creating an agent."""


class AgentUpdate(BaseModel):
    """Payload for updating an agent."""

    name: str | None = Field(None, min_length=1, max_length=128)
    role: str | None = None
    description: str | None = None
    instructions: str | None = None
    model_id: int | None = None
    tool_ids: list[int] | None = None
    knowledge_ids: list[int] | None = None
    extra_config: dict[str, Any] | None = None


class AgentRead(AgentBase):
    """Agent as returned by the API."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
