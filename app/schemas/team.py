"""Pydantic schemas for teams."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

TeamMode = Literal["coordinate", "route", "collaborate"]


class TeamBase(BaseModel):
    """Shared team fields."""

    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None
    mode: TeamMode = "coordinate"
    instructions: str | None = None
    model_id: int | None = None
    member_agent_ids: list[int] | None = None
    tool_ids: list[int] | None = None
    knowledge_ids: list[int] | None = None
    extra_config: dict[str, Any] | None = None


class TeamCreate(TeamBase):
    """Payload for creating a team."""


class TeamUpdate(BaseModel):
    """Payload for updating a team."""

    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = None
    mode: TeamMode | None = None
    instructions: str | None = None
    model_id: int | None = None
    member_agent_ids: list[int] | None = None
    tool_ids: list[int] | None = None
    knowledge_ids: list[int] | None = None
    extra_config: dict[str, Any] | None = None


class TeamRead(TeamBase):
    """Team as returned by the API."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
