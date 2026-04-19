"""Execute agents and teams built from stored configuration."""

import json
from collections.abc import Iterator
from typing import Any

from sqlalchemy.orm import Session

from app.agno_integration.factory import build_agno_agent, build_agno_team
from app.core.exceptions import ProviderError
from app.core.logging_config import get_logger
from app.models.agent import Agent as AgentModel
from app.models.team import Team as TeamModel
from app.schemas.run import RunRequest, RunResponse
from app.services.agent_service import agent_service
from app.services.team_service import team_service

logger = get_logger(__name__)


def run_agent(db: Session, agent_id: int, payload: RunRequest) -> RunResponse:
    """Build the Agno agent for ``agent_id`` and run the prompt against it."""
    agent_row: AgentModel = agent_service.get(db, agent_id)
    logger.info("Running agent id=%s name=%s", agent_row.id, agent_row.name)

    agno_agent = build_agno_agent(db, agent_row)
    response = _invoke_run(agno_agent, payload)

    return _to_run_response(agent_row.id, "agent", response)


def run_team(db: Session, team_id: int, payload: RunRequest) -> RunResponse:
    """Build the Agno team for ``team_id`` and run the prompt against it."""
    team_row: TeamModel = team_service.get(db, team_id)
    logger.info("Running team id=%s name=%s", team_row.id, team_row.name)

    agno_team = build_agno_team(db, team_row)
    response = _invoke_run(agno_team, payload)

    return _to_run_response(team_row.id, "team", response)


def stream_agent(db: Session, agent_id: int, payload: RunRequest) -> Iterator[str]:
    """Build the Agno agent and yield SSE-formatted chunks as they arrive."""
    agent_row: AgentModel = agent_service.get(db, agent_id)
    logger.info("Streaming agent id=%s name=%s", agent_row.id, agent_row.name)
    agno_agent = build_agno_agent(db, agent_row)
    return _stream_run(agno_agent, payload, agent_row.id, "agent")


def stream_team(db: Session, team_id: int, payload: RunRequest) -> Iterator[str]:
    """Build the Agno team and yield SSE-formatted chunks as they arrive."""
    team_row: TeamModel = team_service.get(db, team_id)
    logger.info("Streaming team id=%s name=%s", team_row.id, team_row.name)
    agno_team = build_agno_team(db, team_row)
    return _stream_run(agno_team, payload, team_row.id, "team")


def _build_kwargs(payload: RunRequest, *, stream: bool) -> dict[str, Any]:
    """Merge the RunRequest optional fields into a kwargs dict for Agno."""
    kwargs: dict[str, Any] = dict(payload.extra or {})
    if payload.session_id is not None:
        kwargs.setdefault("session_id", payload.session_id)
    if payload.user_id is not None:
        kwargs.setdefault("user_id", payload.user_id)
    if stream:
        kwargs["stream"] = True
    return kwargs


def _invoke_run(runnable: Any, payload: RunRequest) -> Any:
    """Invoke ``.run()`` on an Agno Agent or Team in non-streaming mode."""
    kwargs = _build_kwargs(payload, stream=False)
    try:
        return runnable.run(payload.message, **kwargs)
    except TypeError:
        # Some Agno versions accept ``message=`` as a keyword argument only.
        return runnable.run(message=payload.message, **kwargs)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Run failed: %s", exc)
        raise ProviderError(f"Failed to execute run: {exc}") from exc


def _stream_run(
    runnable: Any, payload: RunRequest, resource_id: int, kind: str
) -> Iterator[str]:
    """Yield Server-Sent-Events for each Agno streaming chunk."""
    kwargs = _build_kwargs(payload, stream=True)

    try:
        try:
            iterator = runnable.run(payload.message, **kwargs)
        except TypeError:
            iterator = runnable.run(message=payload.message, **kwargs)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Stream setup failed: %s", exc)
        yield _sse({"error": f"Failed to start stream: {exc}"})
        return

    try:
        for event in iterator:
            content = getattr(event, "content", None)
            if content is None and isinstance(event, str):
                content = event
            if content:
                yield _sse({"content": str(content)})
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Stream failed: %s", exc)
        yield _sse({"error": str(exc)})
        return

    yield _sse({"done": True, "id": resource_id, "kind": kind})


def _sse(payload: dict[str, Any]) -> str:
    """Format a dict payload as a Server-Sent-Events data frame."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _to_run_response(resource_id: int, kind: str, response: Any) -> RunResponse:
    """Normalize an Agno RunResponse into our API schema."""
    content = getattr(response, "content", None)
    if content is None and isinstance(response, str):
        content = response
    if content is None:
        content = str(response)

    run_id = getattr(response, "run_id", None)
    metrics = _jsonable(getattr(response, "metrics", None))
    if metrics is not None and not isinstance(metrics, dict):
        metrics = {"raw": metrics}

    return RunResponse(
        id=resource_id,
        kind=kind,
        content=str(content),
        run_id=str(run_id) if run_id is not None else None,
        metrics=metrics,
    )


def _jsonable(obj: Any) -> Any:
    """Recursively convert ``obj`` into a JSON-serializable structure.

    Agno returns metrics as custom objects (e.g. ``agno.utils.timer.Timer``)
    that Pydantic cannot serialize by default. We walk the structure and
    coerce anything exotic into a primitive representation.
    """
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple, set)):
        return [_jsonable(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if hasattr(obj, "model_dump"):
        try:
            return _jsonable(obj.model_dump())
        except Exception:  # pragma: no cover - defensive
            pass
    if hasattr(obj, "__dict__") and obj.__dict__:
        return _jsonable(vars(obj))
    return str(obj)
