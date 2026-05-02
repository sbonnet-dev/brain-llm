"""Chat sessions REST API."""

from fastapi import APIRouter, Query

from app.schemas.common import ErrorResponse
from app.schemas.session import SessionDeleteResponse, SessionHistory, SessionSummary
from app.services import session_service

router = APIRouter(prefix="/sessions", tags=["sessions"])

_ERROR_RESPONSES = {
    404: {"model": ErrorResponse},
    502: {"model": ErrorResponse},
}


@router.get(
    "",
    response_model=list[SessionSummary],
    summary="List chat sessions for a user",
)
def list_sessions(
    user_id: str = Query(..., description="Owner of the sessions to list"),
) -> list[SessionSummary]:
    """Return every session belonging to ``user_id`` across agents and teams."""
    return session_service.list_sessions(user_id=user_id)


@router.get(
    "/{session_id}/history",
    response_model=SessionHistory,
    responses=_ERROR_RESPONSES,
    summary="Get the full message history of a session",
)
def get_session_history(session_id: str) -> SessionHistory:
    """Return all messages stored for ``session_id``."""
    return session_service.get_history(session_id=session_id)


@router.delete(
    "/{session_id}",
    response_model=SessionDeleteResponse,
    responses=_ERROR_RESPONSES,
    summary="Delete a chat session",
)
def delete_session(session_id: str) -> SessionDeleteResponse:
    """Delete ``session_id`` and its full memory."""
    return session_service.delete_session(session_id=session_id)
