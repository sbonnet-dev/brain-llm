"""Request and response schemas for agent/team execution."""

from typing import Any

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    """Payload for executing an agent or a team."""

    message: str = Field(..., min_length=1, description="Prompt or instruction to run")
    session_id: str | None = Field(
        None,
        description="Optional session identifier, used by Agno to keep memory context.",
    )
    user_id: str | None = Field(
        None,
        description="Optional user identifier forwarded to the Agno runtime.",
    )
    stream: bool = Field(
        False,
        description=(
            "If true, the response is streamed as Server-Sent Events "
            "(text/event-stream). Each event is a JSON object "
            "`{\"content\": \"...\"}` followed by a final "
            "`{\"done\": true}` marker."
        ),
    )
    extra: dict[str, Any] | None = Field(
        None,
        description="Additional keyword arguments forwarded to Agent/Team .run().",
    )


class RunResponse(BaseModel):
    """Response returned after a successful run."""

    id: int = Field(..., description="Id of the executed agent or team")
    kind: str = Field(..., description="'agent' or 'team'")
    content: str = Field(..., description="Final answer produced by the agent/team")
    run_id: str | None = Field(None, description="Agno run identifier, when available")
    metrics: dict[str, Any] | None = Field(
        None,
        description="Metrics reported by Agno (tokens, timings, ...).",
    )
