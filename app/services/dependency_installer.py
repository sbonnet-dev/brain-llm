"""Install pip dependencies declared on Tool records.

Tools may declare a comma-separated ``dependencies`` field (e.g.
``"yfinance,duckduckgo-search"``). Packages are installed via ``pip`` into the
running interpreter's environment so they can be imported when the tool is
instantiated. Already-installed packages are skipped.
"""

from __future__ import annotations

import importlib.metadata
import re
import subprocess
import sys

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.models.tool import Tool

logger = get_logger(__name__)

# Strip version specifiers / extras / markers to get the bare distribution name.
_NAME_SPLIT = re.compile(r"[<>=!~ \[;]")


def parse_dependencies(value: str | None) -> list[str]:
    """Split a comma-separated dependency string into individual specifiers."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _is_installed(spec: str) -> bool:
    """Return True if a distribution matching ``spec``'s name is already installed."""
    name = _NAME_SPLIT.split(spec, 1)[0].strip()
    if not name:
        return False
    try:
        importlib.metadata.distribution(name)
        return True
    except importlib.metadata.PackageNotFoundError:
        return False


def install_dependency(spec: str) -> None:
    """Install a single pip spec via the current interpreter, skipping if present."""
    if _is_installed(spec):
        logger.debug("Dependency %s already installed, skipping", spec)
        return
    logger.info("Installing tool dependency: %s", spec)
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", spec],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        logger.error(
            "pip install %s failed (exit=%s): %s",
            spec,
            exc.returncode,
            (exc.stderr or exc.stdout or "").strip(),
        )
        raise


def install_dependencies(value: str | None) -> None:
    """Install every package listed in a comma-separated dependency string."""
    for spec in parse_dependencies(value):
        install_dependency(spec)


def install_all_tool_dependencies(db: Session) -> None:
    """Install dependencies declared by every tool currently in the database."""
    tools = db.query(Tool).all()
    for tool in tools:
        if not tool.dependencies:
            continue
        try:
            install_dependencies(tool.dependencies)
        except Exception as exc:  # pragma: no cover - keep startup resilient
            logger.warning(
                "Failed to install dependencies for tool '%s' (id=%s): %s",
                tool.name,
                tool.id,
                exc,
            )
