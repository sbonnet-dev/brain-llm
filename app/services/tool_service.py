"""CRUD service for tools, including upload of Python toolkit files."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.models.tool import Tool
from app.schemas.tool import ToolCreate, ToolUpdate
from app.services.base import CRUDBase

logger = get_logger(__name__)


def _storage_dir() -> Path:
    path = Path(get_settings().tool_storage_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def tool_source_path(tool_id: int) -> Path:
    """Return the on-disk path of the Python source for a given tool id."""
    return _storage_dir() / f"{tool_id}.py"


class ToolService(CRUDBase[Tool, ToolCreate, ToolUpdate]):
    """Tool CRUD that also wipes the Python source file on delete."""

    def delete(self, db: Session, item_id: int) -> int:
        result = super().delete(db, item_id)
        path = tool_source_path(item_id)
        if path.exists():
            try:
                path.unlink()
            except OSError as exc:
                logger.warning("Failed to remove tool source %s: %s", path, exc)
        return result


tool_service: ToolService = ToolService(Tool, "Tool")


def write_tool_source(tool_id: int, content: bytes) -> None:
    """Persist raw bytes as the Python source backing a python_file tool."""
    path = tool_source_path(tool_id)
    path.write_bytes(content)
    os.chmod(path, 0o600)


def read_tool_source(tool_id: int) -> bytes:
    """Read the Python source for a tool, or raise FileNotFoundError."""
    return tool_source_path(tool_id).read_bytes()
