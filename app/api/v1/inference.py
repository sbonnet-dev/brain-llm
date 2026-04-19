"""Inference REST API.

Dedicated router for executing agents and teams.  Having its own tag
ensures the run endpoints appear as a clearly identifiable section in the
Swagger UI, separate from the CRUD operations.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import ErrorResponse
from app.schemas.run import RunRequest, RunResponse
from app.services.run_service import run_agent, run_team

router = APIRouter(prefix="/inference", tags=["inference"])

_ERROR_RESPONSES = {
    400: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    502: {"model": ErrorResponse},
}


@router.post(
    "/agents/{agent_id}/run",
    response_model=RunResponse,
    responses=_ERROR_RESPONSES,
    summary="Run an agent",
    description=(
        "Build the Agno agent from its stored configuration, send the message "
        "to the configured LLM provider and return the generated answer together "
        "with optional run metadata (run_id, metrics)."
    ),
)
def execute_agent(
    agent_id: int,
    payload: RunRequest,
    db: Session = Depends(get_db),
) -> RunResponse:
    """Execute an agent synchronously and return the result."""
    return run_agent(db, agent_id, payload)


@router.post(
    "/teams/{team_id}/run",
    response_model=RunResponse,
    responses=_ERROR_RESPONSES,
    summary="Run a team",
    description=(
        "Build the Agno team from its stored configuration (leader model + "
        "member agents), run the message through the team and return the "
        "consolidated answer."
    ),
)
def execute_team(
    team_id: int,
    payload: RunRequest,
    db: Session = Depends(get_db),
) -> RunResponse:
    """Execute a team synchronously and return the result."""
    return run_team(db, team_id, payload)
