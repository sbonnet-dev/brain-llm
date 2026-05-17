"""CRUD service for tools, including upload of Python toolkit files."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.models.agent import Agent
from app.models.team import Team
from app.models.tool import Tool
from app.schemas.tool import ToolCreate, ToolUpdate
from app.services.base import CRUDBase

logger = get_logger(__name__)


def _storage_dir() -> Path:
    path = Path(get_settings().tool_storage_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def tool_source_path(tool_id: int) -> Path:
    """Return the on-disk path of the Python source for a given tool id."""
    return _storage_dir() / f"{tool_id}.py"


def list_tool_usage(db: Session, tool_id: int) -> dict[str, list[dict]]:
    """Return the agents and teams that reference ``tool_id``."""
    agents = db.execute(select(Agent).order_by(Agent.name)).scalars().all()
    teams = db.execute(select(Team).order_by(Team.name)).scalars().all()
    return {
        "agents": [
            {"id": agent.id, "name": agent.name}
            for agent in agents
            if _has_tool(agent.tool_ids, tool_id)
        ],
        "teams": [
            {"id": team.id, "name": team.name}
            for team in teams
            if _has_tool(team.tool_ids, tool_id)
        ],
    }


def _has_tool(tool_ids: list | None, tool_id: int) -> bool:
    if not tool_ids:
        return False
    return tool_id in tool_ids


def _detach_tool_from_references(db: Session, tool_id: int) -> None:
    """Remove ``tool_id`` from every agent and team that references it."""
    agents = db.execute(select(Agent)).scalars().all()
    for agent in agents:
        if _has_tool(agent.tool_ids, tool_id):
            agent.tool_ids = [tid for tid in agent.tool_ids if tid != tool_id]
            flag_modified(agent, "tool_ids")

    teams = db.execute(select(Team)).scalars().all()
    for team in teams:
        if _has_tool(team.tool_ids, tool_id):
            team.tool_ids = [tid for tid in team.tool_ids if tid != tool_id]
            flag_modified(team, "tool_ids")

    db.commit()


class ToolService(CRUDBase[Tool, ToolCreate, ToolUpdate]):
    """Tool CRUD that also wipes the Python source file on delete."""

    def delete(self, db: Session, item_id: int) -> int:
        _detach_tool_from_references(db, item_id)
        result = super().delete(db, item_id)
        path = tool_source_path(item_id)
        if path.exists():
            try:
                path.unlink()
            except OSError as exc:
                logger.warning("Failed to remove tool source %s: %s", path, exc)
        return result


tool_service: ToolService = ToolService(Tool, "Tool")


def write_tool_source(tool_id: int, content: bytes) -> None:
    """Persist raw bytes as the Python source backing a python_file tool."""
    path = tool_source_path(tool_id)
    path.write_bytes(content)
    os.chmod(path, 0o600)


def read_tool_source(tool_id: int) -> bytes:
    """Read the Python source for a tool, or raise FileNotFoundError."""
    return tool_source_path(tool_id).read_bytes()
