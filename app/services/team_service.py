"""CRUD service for teams."""

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.agent import Agent
from app.models.knowledge import Knowledge
from app.models.model import Model
from app.models.team import Team
from app.models.tool import Tool
from app.schemas.team import TeamCreate, TeamUpdate
from app.services.base import CRUDBase


class TeamService(CRUDBase[Team, TeamCreate, TeamUpdate]):
    """Team CRUD with referential-integrity checks."""

    def create(self, db: Session, payload: TeamCreate) -> Team:
        """Validate references and persist the team."""
        _validate_team_refs(db, payload)
        return super().create(db, payload)

    def update(self, db: Session, item_id: int, payload: TeamUpdate) -> Team:
        """Validate references and update the team."""
        _validate_team_refs(db, payload)
        return super().update(db, item_id, payload)


def _validate_team_refs(db: Session, payload: TeamCreate | TeamUpdate) -> None:
    """Ensure every referenced entity exists."""
    data = payload.model_dump(exclude_unset=True)

    model_id = data.get("model_id")
    if model_id is not None and db.get(Model, model_id) is None:
        raise ValidationError(f"Model with id={model_id} does not exist")

    for agent_id in data.get("member_agent_ids") or []:
        if db.get(Agent, agent_id) is None:
            raise ValidationError(f"Agent with id={agent_id} does not exist")

    for tool_id in data.get("tool_ids") or []:
        if db.get(Tool, tool_id) is None:
            raise ValidationError(f"Tool with id={tool_id} does not exist")

    for knowledge_id in data.get("knowledge_ids") or []:
        if db.get(Knowledge, knowledge_id) is None:
            raise ValidationError(f"Knowledge with id={knowledge_id} does not exist")


team_service = TeamService(Team, "Team")
