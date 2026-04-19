"""Tools REST API."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import DeleteResponse, ErrorResponse
from app.schemas.tool import ToolCreate, ToolRead, ToolUpdate
from app.services.tool_service import tool_service

router = APIRouter(prefix="/tools", tags=["tools"])

_ERROR_RESPONSES = {
    400: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
}


@router.get("", response_model=list[ToolRead], summary="List tools")
def list_tools(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[ToolRead]:
    """Return a paginated list of tools."""
    return tool_service.list(db, skip=skip, limit=limit)


@router.get(
    "/{tool_id}",
    response_model=ToolRead,
    responses=_ERROR_RESPONSES,
    summary="Get a tool",
)
def get_tool(tool_id: int, db: Session = Depends(get_db)) -> ToolRead:
    """Fetch a single tool by id."""
    return tool_service.get(db, tool_id)


@router.post(
    "",
    response_model=ToolRead,
    status_code=status.HTTP_201_CREATED,
    responses=_ERROR_RESPONSES,
    summary="Create a tool",
)
def create_tool(payload: ToolCreate, db: Session = Depends(get_db)) -> ToolRead:
    """Create a new tool."""
    return tool_service.create(db, payload)


@router.patch(
    "/{tool_id}",
    response_model=ToolRead,
    responses=_ERROR_RESPONSES,
    summary="Update a tool",
)
def update_tool(
    tool_id: int,
    payload: ToolUpdate,
    db: Session = Depends(get_db),
) -> ToolRead:
    """Partially update an existing tool."""
    return tool_service.update(db, tool_id, payload)


@router.delete(
    "/{tool_id}",
    response_model=DeleteResponse,
    responses=_ERROR_RESPONSES,
    summary="Delete a tool",
)
def delete_tool(tool_id: int, db: Session = Depends(get_db)) -> DeleteResponse:
    """Delete a tool by id."""
    return DeleteResponse(id=tool_service.delete(db, tool_id))
