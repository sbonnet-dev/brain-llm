"""Pydantic schemas for skills."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

_SLUG_RE = r"^[a-z0-9-]+$"


class SkillBase(BaseModel):
    """Shared skill fields."""

    name: str = Field(..., min_length=1, max_length=150)
    slug: str = Field(..., min_length=1, max_length=150, pattern=_SLUG_RE)
    content: str = Field("", description="Free-form skill body.")

    @field_validator("slug")
    @classmethod
    def _normalize_slug(cls, v: str) -> str:
        return v.lower()


class SkillCreate(SkillBase):
    """Payload for creating a skill."""


class SkillUpdate(BaseModel):
    """Payload for updating a skill."""

    name: str | None = Field(None, min_length=1, max_length=150)
    slug: str | None = Field(None, min_length=1, max_length=150, pattern=_SLUG_RE)
    content: str | None = None

    @field_validator("slug")
    @classmethod
    def _normalize_slug(cls, v: str | None) -> str | None:
        return v.lower() if v else v


class SkillRead(SkillBase):
    """Skill as returned by the API."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
