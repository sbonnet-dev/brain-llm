"""CRUD service for tools."""

from app.models.tool import Tool
from app.schemas.tool import ToolCreate, ToolUpdate
from app.services.base import CRUDBase

tool_service: CRUDBase[Tool, ToolCreate, ToolUpdate] = CRUDBase(Tool, "Tool")
