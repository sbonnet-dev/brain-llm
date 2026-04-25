"""CRUD service for agents."""

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.agent import Agent
from app.models.knowledge import Knowledge
from app.models.model import Model
from app.models.suggestion import Suggestion
from app.schemas.agent import SuggestionCreate
from app.models.tool import Tool
from app.schemas.agent import AgentCreate, AgentUpdate
from app.services.base import CRUDBase


class AgentService(CRUDBase[Agent, AgentCreate, AgentUpdate]):
    """Agent CRUD with referential-integrity checks."""

    def create(self, db: Session, payload: AgentCreate) -> Agent:
        _validate_references(
            db,
            model_id=payload.model_id,
            tool_ids=payload.tool_ids,
            knowledge_ids=payload.knowledge_ids,
        )
        suggestions = payload.suggestions
        clean = AgentCreate(**payload.model_dump(exclude={"suggestions"}))
        agent = super().create(db, clean)
        _replace_suggestions(db, agent, suggestions)
        return agent

    def update(self, db: Session, item_id: int, payload: AgentUpdate) -> Agent:
        _validate_references(
            db,
            model_id=payload.model_id,
            tool_ids=payload.tool_ids,
            knowledge_ids=payload.knowledge_ids,
        )
        suggestions = payload.suggestions
        clean = AgentUpdate(**payload.model_dump(exclude={"suggestions"}, exclude_unset=True))
        agent = super().update(db, item_id, clean)
        if suggestions is not None:
            _replace_suggestions(db, agent, suggestions)
        return agent


def _validate_references(
    db: Session,
    *,
    model_id: int | None,
    tool_ids: list[int] | None,
    knowledge_ids: list[int] | None,
) -> None:
    """Ensure referenced model/tools/knowledges exist."""
    if model_id is not None and db.get(Model, model_id) is None:
        raise ValidationError(f"Model with id={model_id} does not exist")
    for tool_id in tool_ids or []:
        if db.get(Tool, tool_id) is None:
            raise ValidationError(f"Tool with id={tool_id} does not exist")
    for knowledge_id in knowledge_ids or []:
        if db.get(Knowledge, knowledge_id) is None:
            raise ValidationError(f"Knowledge with id={knowledge_id} does not exist")


def _replace_suggestions(
    db: Session,
    agent: Agent,
    suggestions: list[SuggestionCreate] | None,
) -> None:
    """Delete existing suggestions for the agent and insert the new ones."""
    db.query(Suggestion).filter(Suggestion.agent_id == agent.id).delete()
    for s in suggestions or []:
        db.add(Suggestion(agent_id=agent.id, title=s.title, icon=s.icon, prompt=s.prompt))
    db.commit()
    db.refresh(agent)


agent_service = AgentService(Agent, "Agent")
