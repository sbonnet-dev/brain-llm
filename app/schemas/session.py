"""Schemas for chat session history exposed via the API."""

from pydantic import BaseModel, Field


class SessionMessage(BaseModel):
    """A single message stored in a session's memory."""

    role: str = Field(..., description="Message author role: 'user', 'assistant', 'system', 'tool'")
    content: str = Field(..., description="Message content")


class SessionSummary(BaseModel):
    """Lightweight session record returned in the session list."""

    session_id: str
    user_id: str | None = None
    entity_id: str | None = Field(
        None,
        description="Identifier of the agent or team that produced this session.",
    )
    kind: str = Field(..., description="'agent' or 'team'")
    title: str = Field(..., description="Short label derived from the first user message")
    created_at: int | None = None
    updated_at: int | None = None


class SessionHistory(BaseModel):
    """Full message history for a single session."""

    session_id: str
    user_id: str | None = None
    entity_id: str | None = None
    kind: str
    messages: list[SessionMessage]
    created_at: int | None = None
    updated_at: int | None = None


class SessionDeleteResponse(BaseModel):
    """Response after a session deletion."""

    session_id: str
    deleted: bool = True
