"""Tools REST API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NotFoundError, ValidationError
from app.schemas.common import DeleteResponse, ErrorResponse
from app.schemas.tool import ToolCreate, ToolRead, ToolUpdate
from app.services.dependency_installer import install_dependencies
from app.services.tool_service import (
    read_tool_source,
    tool_service,
    tool_source_path,
    write_tool_source,
)

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
    summary="Create a tool by uploading a Python toolkit file",
)
async def create_tool(
    name: str = Form(..., description="Unique tool name"),
    description: str | None = Form(None),
    dependencies: str | None = Form(
        None,
        description="Comma-separated pip packages to install before using the tool (e.g. 'yfinance,duckduckgo-search').",
    ),
    file: UploadFile = File(..., description="Python file containing an Agno Toolkit subclass"),
    db: Session = Depends(get_db),
) -> ToolRead:
    """Create a tool by uploading a .py file containing an Agno Toolkit.

    The file must define either a module-level instance named ``toolkit`` or
    at least one ``agno.tools.Toolkit`` subclass.
    """
    filename = file.filename or "tool.py"
    if not filename.endswith(".py"):
        raise ValidationError("Uploaded file must have a .py extension")

    content = await file.read()

    payload = ToolCreate(
        name=name,
        kind="python_file",
        reference=filename,
        description=description,
        dependencies=dependencies,
    )
    tool = tool_service.create(db, payload)
    try:
        write_tool_source(tool.id, content)
    except Exception:
        # Roll back the DB row if we cannot persist the source on disk.
        tool_service.delete(db, tool.id)
        raise
    if dependencies:
        try:
            install_dependencies(dependencies)
        except Exception as exc:
            raise ValidationError(f"Failed to install tool dependencies: {exc}") from exc
    return tool


@router.get(
    "/{tool_id}/source",
    responses={**_ERROR_RESPONSES, 200: {"content": {"text/x-python": {}}}},
    summary="Download the Python source of a python_file tool",
)
def get_tool_source(tool_id: int, db: Session = Depends(get_db)) -> Response:
    tool = tool_service.get(db, tool_id)
    if tool.kind != "python_file":
        raise ValidationError("This tool does not have a Python source file")
    if not tool_source_path(tool_id).exists():
        raise NotFoundError(f"Source file for tool id={tool_id} is missing")
    data = read_tool_source(tool_id)
    headers = {"Content-Disposition": f'attachment; filename="{tool.reference}"'}
    return Response(content=data, media_type="text/x-python", headers=headers)


@router.put(
    "/{tool_id}/source",
    response_model=ToolRead,
    responses=_ERROR_RESPONSES,
    summary="Replace the Python source of a python_file tool",
)
async def update_tool_source(
    tool_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ToolRead:
    tool = tool_service.get(db, tool_id)
    if tool.kind != "python_file":
        raise ValidationError("This tool does not have a Python source file")
    filename = file.filename or tool.reference
    if not filename.endswith(".py"):
        raise ValidationError("Uploaded file must have a .py extension")
    content = await file.read()
    write_tool_source(tool_id, content)
    if filename != tool.reference:
        tool = tool_service.update(db, tool_id, ToolUpdate(reference=filename))
    return tool


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
    tool = tool_service.update(db, tool_id, payload)
    if payload.dependencies:
        try:
            install_dependencies(payload.dependencies)
        except Exception as exc:
            raise ValidationError(f"Failed to install tool dependencies: {exc}") from exc
    return tool


@router.delete(
    "/{tool_id}",
    response_model=DeleteResponse,
    responses=_ERROR_RESPONSES,
    summary="Delete a tool",
)
def delete_tool(tool_id: int, db: Session = Depends(get_db)) -> DeleteResponse:
    """Delete a tool by id."""
    return DeleteResponse(id=tool_service.delete(db, tool_id))
