"""CRUD service for agents."""

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.agent import Agent
from app.models.knowledge import Knowledge
from app.models.provider import Provider
from app.models.tool import Tool
from app.schemas.agent import AgentCreate, AgentUpdate
from app.services.base import CRUDBase


class AgentService(CRUDBase[Agent, AgentCreate, AgentUpdate]):
    """Agent CRUD with referential-integrity checks."""

    def create(self, db: Session, payload: AgentCreate) -> Agent:
        """Validate references then delegate to the generic creator."""
        _validate_references(
            db,
            provider_id=payload.provider_id,
            tool_ids=payload.tool_ids,
            knowledge_ids=payload.knowledge_ids,
        )
        return super().create(db, payload)

    def update(self, db: Session, item_id: int, payload: AgentUpdate) -> Agent:
        """Validate referenced resources on update."""
        _validate_references(
            db,
            provider_id=payload.provider_id,
            tool_ids=payload.tool_ids,
            knowledge_ids=payload.knowledge_ids,
        )
        return super().update(db, item_id, payload)


def _validate_references(
    db: Session,
    *,
    provider_id: int | None,
    tool_ids: list[int] | None,
    knowledge_ids: list[int] | None,
) -> None:
    """Ensure referenced provider/tools/knowledges exist."""
    if provider_id is not None and db.get(Provider, provider_id) is None:
        raise ValidationError(f"Provider with id={provider_id} does not exist")
    for tool_id in tool_ids or []:
        if db.get(Tool, tool_id) is None:
            raise ValidationError(f"Tool with id={tool_id} does not exist")
    for knowledge_id in knowledge_ids or []:
        if db.get(Knowledge, knowledge_id) is None:
            raise ValidationError(f"Knowledge with id={knowledge_id} does not exist")


agent_service = AgentService(Agent, "Agent")
