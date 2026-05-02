"""Assemble Agno Agents, Teams, and the AgentOS application.

Inspired by https://docs.agno.com/agent-os/usage/demo.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.agno_integration.knowledge_builder import build_knowledge
from app.agno_integration.model_builder import build_model
from app.agno_integration.storage_builder import get_session_db
from app.agno_integration.tool_builder import build_tool
from app.core.exceptions import NotFoundError
from app.core.logging_config import get_logger
from app.models.agent import Agent as AgentModel
from app.models.knowledge import Knowledge
from app.models.model import Model
from app.models.provider import Provider
from app.models.team import Team as TeamModel
from app.models.tool import Tool

logger = get_logger(__name__)


def build_agno_agent(db: Session, agent_row: AgentModel) -> Any:
    """Translate an Agent DB record into a runnable ``agno.agent.Agent``."""
    from agno.agent import Agent as AgnoAgent  # type: ignore

    model_row = _must_get(db, Model, agent_row.model_id, "Model")
    provider = _must_get(db, Provider, model_row.provider_id, "Provider")

    model = build_model(provider, model_row.name, model_row.extra_config)
    tools = _resolve_tools(db, agent_row.tool_ids or [])
    knowledge = _resolve_first_knowledge(db, agent_row.knowledge_ids or [])

    kwargs: dict[str, Any] = dict(agent_row.extra_config or {})
    kwargs.pop("is_active", None)
    kwargs.pop("group_ids", None)
    if agent_row.role is not None:
        kwargs.setdefault("role", agent_row.role)
    if agent_row.description is not None:
        kwargs.setdefault("description", agent_row.description)
    if agent_row.instructions is not None:
        kwargs.setdefault("instructions", agent_row.instructions)

    return AgnoAgent(
        name=agent_row.name,
        model=model,
        tools=tools or None,
        knowledge=knowledge,
        db=get_session_db(),
        add_history_to_context=True,
        num_history_runs=10,
        **kwargs,
    )


def build_agno_team(db: Session, team_row: TeamModel) -> Any:
    """Translate a Team DB record into a runnable ``agno.team.Team``."""
    from agno.team import Team as AgnoTeam  # type: ignore

    members = [
        build_agno_agent(db, _must_get(db, AgentModel, aid, "Agent"))
        for aid in team_row.member_agent_ids or []
    ]

    leader_model = None
    if team_row.model_id is not None:
        model_row = _must_get(db, Model, team_row.model_id, "Model")
        provider = _must_get(db, Provider, model_row.provider_id, "Provider")
        leader_model = build_model(provider, model_row.name, model_row.extra_config)

    tools = _resolve_tools(db, team_row.tool_ids or [])
    knowledge = _resolve_first_knowledge(db, team_row.knowledge_ids or [])

    kwargs: dict[str, Any] = dict(team_row.extra_config or {})
    kwargs.pop("is_active", None)
    kwargs.pop("group_ids", None)
    if team_row.description is not None:
        kwargs.setdefault("description", team_row.description)
    if team_row.instructions is not None:
        kwargs.setdefault("instructions", team_row.instructions)

    return AgnoTeam(
        name=team_row.name,
        mode=team_row.mode,
        members=members,
        model=leader_model,
        tools=tools or None,
        knowledge=knowledge,
        db=get_session_db(),
        **kwargs,
    )


def build_agent_os(db: Session) -> Any:
    """Build an AgentOS application aggregating every stored agent and team."""
    from agno.os import AgentOS  # type: ignore

    agents = [build_agno_agent(db, row) for row in db.query(AgentModel).all()]
    teams = [build_agno_team(db, row) for row in db.query(TeamModel).all()]
    logger.info("AgentOS built: %d agents, %d teams", len(agents), len(teams))
    return AgentOS(agents=agents, teams=teams)


def _resolve_tools(db: Session, tool_ids: list[int]) -> list[Any]:
    """Load Tool rows and instantiate them."""
    return [build_tool(_must_get(db, Tool, tid, "Tool")) for tid in tool_ids]


def _resolve_first_knowledge(db: Session, ids: list[int]) -> Any | None:
    """Return the first knowledge base referenced, if any."""
    if not ids:
        return None
    return build_knowledge(db, _must_get(db, Knowledge, ids[0], "Knowledge"))


def _must_get(db: Session, model: type, item_id: int, name: str) -> Any:
    """Fetch an ORM row or raise NotFoundError."""
    item = db.get(model, item_id)
    if item is None:
        raise NotFoundError(f"{name} with id={item_id} not found")
    return item
