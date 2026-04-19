"""Agents REST API."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.agent import AgentCreate, AgentRead, AgentUpdate
from app.schemas.common import DeleteResponse, ErrorResponse
from app.schemas.run import RunRequest, RunResponse
from app.services.agent_service import agent_service
from app.services.run_service import run_agent

router = APIRouter(prefix="/agents", tags=["agents"])

_ERROR_RESPONSES = {
    400: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    502: {"model": ErrorResponse},
}


@router.get("", response_model=list[AgentRead], summary="List agents")
def list_agents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[AgentRead]:
    """Return a paginated list of agents."""
    return agent_service.list(db, skip=skip, limit=limit)


@router.get(
    "/{agent_id}",
    response_model=AgentRead,
    responses=_ERROR_RESPONSES,
    summary="Get an agent",
)
def get_agent(agent_id: int, db: Session = Depends(get_db)) -> AgentRead:
    """Fetch a single agent by id."""
    return agent_service.get(db, agent_id)


@router.post(
    "",
    response_model=AgentRead,
    status_code=status.HTTP_201_CREATED,
    responses=_ERROR_RESPONSES,
    summary="Create an agent",
)
def create_agent(payload: AgentCreate, db: Session = Depends(get_db)) -> AgentRead:
    """Create a new agent."""
    return agent_service.create(db, payload)


@router.patch(
    "/{agent_id}",
    response_model=AgentRead,
    responses=_ERROR_RESPONSES,
    summary="Update an agent",
)
def update_agent(
    agent_id: int,
    payload: AgentUpdate,
    db: Session = Depends(get_db),
) -> AgentRead:
    """Partially update an existing agent."""
    return agent_service.update(db, agent_id, payload)


@router.delete(
    "/{agent_id}",
    response_model=DeleteResponse,
    responses=_ERROR_RESPONSES,
    summary="Delete an agent",
)
def delete_agent(agent_id: int, db: Session = Depends(get_db)) -> DeleteResponse:
    """Delete an agent by id."""
    return DeleteResponse(id=agent_service.delete(db, agent_id))


@router.post(
    "/{agent_id}/run",
    response_model=RunResponse,
    responses=_ERROR_RESPONSES,
    summary="Execute an agent",
    description=(
        "Build the Agno agent from its stored configuration, run the provided "
        "message and return the generated answer."
    ),
)
def execute_agent(
    agent_id: int,
    payload: RunRequest,
    db: Session = Depends(get_db),
) -> RunResponse:
    """Run an agent synchronously and return the result."""
    return run_agent(db, agent_id, payload)
