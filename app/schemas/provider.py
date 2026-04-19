"""Pydantic schemas for providers."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProviderKind = Literal["ollama", "vllm", "openai", "openai_compatible"]


class ProviderBase(BaseModel):
    """Shared provider fields."""

    name: str = Field(..., min_length=1, max_length=128)
    kind: ProviderKind
    base_url: str = Field(..., min_length=1)
    api_key: str | None = None
    default_model: str | None = None
    description: str | None = None


class ProviderCreate(ProviderBase):
    """Payload for creating a provider."""


class ProviderUpdate(BaseModel):
    """Payload for updating a provider (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=128)
    kind: ProviderKind | None = None
    base_url: str | None = None
    api_key: str | None = None
    default_model: str | None = None
    description: str | None = None


class ProviderRead(ProviderBase):
    """Provider as returned by the API."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
