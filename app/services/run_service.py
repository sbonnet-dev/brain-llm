"""Execute agents and teams built from stored configuration."""

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


def _invoke_run(runnable: Any, payload: RunRequest) -> Any:
    """Invoke ``.run()`` on an Agno Agent or Team, forwarding optional kwargs."""
    kwargs: dict[str, Any] = dict(payload.extra or {})
    if payload.session_id is not None:
        kwargs.setdefault("session_id", payload.session_id)
    if payload.user_id is not None:
        kwargs.setdefault("user_id", payload.user_id)

    try:
        return runnable.run(payload.message, **kwargs)
    except TypeError:
        # Some Agno versions accept ``message=`` as a keyword argument only.
        return runnable.run(message=payload.message, **kwargs)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Run failed: %s", exc)
        raise ProviderError(f"Failed to execute run: {exc}") from exc


def _to_run_response(resource_id: int, kind: str, response: Any) -> RunResponse:
    """Normalize an Agno RunResponse into our API schema."""
    content = getattr(response, "content", None)
    if content is None and isinstance(response, str):
        content = response
    if content is None:
        content = str(response)

    run_id = getattr(response, "run_id", None)
    metrics = getattr(response, "metrics", None)
    if metrics is not None and not isinstance(metrics, dict):
        metrics = getattr(metrics, "__dict__", None) or {"raw": str(metrics)}

    return RunResponse(
        id=resource_id,
        kind=kind,
        content=str(content),
        run_id=str(run_id) if run_id is not None else None,
        metrics=metrics,
    )
