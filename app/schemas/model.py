"""Pydantic schemas for models."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Supported model types.
ModelType = Literal["llm", "vlm", "embedder", "reranker", "audio"]

MODEL_TYPES: tuple[str, ...] = ("llm", "vlm", "embedder", "reranker", "audio")

# Silence Pydantic's "model_" protected-namespace warning: the field
# ``model_type`` is intentional and is not related to Pydantic internals.
_CFG = ConfigDict(protected_namespaces=())


class ModelTypeInfo(BaseModel):
    """Description of a supported model_type value."""

    value: str = Field(..., description="Identifier to use in the 'model_type' field")
    label: str = Field(..., description="Human-friendly label")
    description: str = Field(..., description="What this model type is for")

    model_config = _CFG


class ModelBase(BaseModel):
    """Shared model fields."""

    name: str = Field(..., min_length=1, max_length=128)
    model_type: ModelType = Field(..., description="Kind of model: llm, vlm, embedder, ...")
    provider_id: int = Field(..., description="Id of the provider exposing this model")
    description: str | None = None
    extra_config: dict[str, Any] | None = None

    model_config = _CFG


class ModelCreate(ModelBase):
    """Payload for creating a model."""


class ModelUpdate(BaseModel):
    """Payload for updating a model."""

    name: str | None = Field(None, min_length=1, max_length=128)
    model_type: ModelType | None = None
    provider_id: int | None = None
    description: str | None = None
    extra_config: dict[str, Any] | None = None

    model_config = _CFG


class ModelRead(ModelBase):
    """Model as returned by the API."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
