"""Pydantic schemas for providers."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# The provider_type drives which Agno model class is used at runtime.
ProviderType = Literal["ollama", "vllm", "openai_compatible", "mistral"]

PROVIDER_TYPES: tuple[str, ...] = ("ollama", "vllm", "openai_compatible", "mistral")


class ProviderTypeInfo(BaseModel):
    """Description of a supported provider_type value."""

    value: str = Field(..., description="Identifier to use in the 'provider_type' field")
    label: str = Field(..., description="Human-friendly label")
    description: str = Field(..., description="What this provider_type is for")


class ProviderBase(BaseModel):
    """Shared provider fields."""

    name: str = Field(..., min_length=1, max_length=128)
    provider_type: ProviderType = Field(
        ...,
        description="Backend type powering this provider.",
    )
    base_url: str = Field(..., min_length=1)
    api_key: str | None = None
    default_model: str | None = None
    description: str | None = None


class ProviderCreate(ProviderBase):
    """Payload for creating a provider."""


class ProviderUpdate(BaseModel):
    """Payload for updating a provider (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=128)
    provider_type: ProviderType | None = None
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
