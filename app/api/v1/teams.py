"""Teams REST API."""

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import DeleteResponse, ErrorResponse
from app.schemas.run import RunRequest, RunResponse
from app.schemas.team import TeamCreate, TeamRead, TeamUpdate
from app.services.run_service import run_team, stream_team
from app.services.team_service import team_service

router = APIRouter(prefix="/teams", tags=["teams"])

_ERROR_RESPONSES = {
    400: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    502: {"model": ErrorResponse},
}


@router.get("", response_model=list[TeamRead], summary="List teams")
def list_teams(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[TeamRead]:
    """Return a paginated list of teams."""
    return team_service.list(db, skip=skip, limit=limit)


@router.get(
    "/{team_id}",
    response_model=TeamRead,
    responses=_ERROR_RESPONSES,
    summary="Get a team",
)
def get_team(team_id: int, db: Session = Depends(get_db)) -> TeamRead:
    """Fetch a single team by id."""
    return team_service.get(db, team_id)


@router.post(
    "",
    response_model=TeamRead,
    status_code=status.HTTP_201_CREATED,
    responses=_ERROR_RESPONSES,
    summary="Create a team",
)
def create_team(payload: TeamCreate, db: Session = Depends(get_db)) -> TeamRead:
    """Create a new team."""
    return team_service.create(db, payload)


@router.patch(
    "/{team_id}",
    response_model=TeamRead,
    responses=_ERROR_RESPONSES,
    summary="Update a team",
)
def update_team(
    team_id: int,
    payload: TeamUpdate,
    db: Session = Depends(get_db),
) -> TeamRead:
    """Partially update an existing team."""
    return team_service.update(db, team_id, payload)


@router.delete(
    "/{team_id}",
    response_model=DeleteResponse,
    responses=_ERROR_RESPONSES,
    summary="Delete a team",
)
def delete_team(team_id: int, db: Session = Depends(get_db)) -> DeleteResponse:
    """Delete a team by id."""
    return DeleteResponse(id=team_service.delete(db, team_id))


@router.post(
    "/{team_id}/run",
    response_model=RunResponse,
    response_model_exclude_none=False,
    responses=_ERROR_RESPONSES,
    summary="Run a team",
    description=(
        "Build the Agno team from its stored configuration (leader + members), "
        "run the provided message and return the generated answer.\n\n"
        "Set `stream: true` in the payload to receive the answer as a "
        "Server-Sent-Events stream (content-type: text/event-stream)."
    ),
)
def execute_team(
    team_id: int,
    payload: RunRequest,
    db: Session = Depends(get_db),
):
    """Execute a team and return the result (JSON or SSE stream)."""
    if payload.stream:
        return StreamingResponse(
            stream_team(db, team_id, payload),
            media_type="text/event-stream",
        )
    return run_team(db, team_id, payload)
