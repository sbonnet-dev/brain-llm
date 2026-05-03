"""Pydantic schemas for agents."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SuggestionBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    icon: str | None = Field(None, max_length=128)
    color: str | None = Field(None, max_length=32)
    prompt: str = Field(..., min_length=1)


class SuggestionCreate(SuggestionBase):
    """Suggestion payload (used inside AgentCreate / AgentUpdate)."""


class SuggestionRead(SuggestionBase):
    """Suggestion as returned by the API."""

    id: int
    agent_id: int

    model_config = ConfigDict(from_attributes=True)


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
    suggestions: list[SuggestionCreate] | None = None


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
    suggestions: list[SuggestionCreate] | None = None


class AgentRead(AgentBase):
    """Agent as returned by the API."""

    id: int
    suggestions: list[SuggestionRead] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
