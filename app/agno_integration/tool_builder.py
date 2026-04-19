"""Instantiate Agno tools from stored Tool records."""

import importlib
from typing import Any

from app.core.exceptions import ValidationError
from app.core.logging_config import get_logger
from app.models.tool import Tool

logger = get_logger(__name__)

# Default lookup for built-in Agno tools (name -> (module, class)).
# Extend this mapping as new tools are exposed by Agno.
BUILTIN_TOOLS: dict[str, tuple[str, str]] = {
    "DuckDuckGoTools": ("agno.tools.duckduckgo", "DuckDuckGoTools"),
    "YFinanceTools": ("agno.tools.yfinance", "YFinanceTools"),
    "GoogleSearchTools": ("agno.tools.googlesearch", "GoogleSearchTools"),
    "WikipediaTools": ("agno.tools.wikipedia", "WikipediaTools"),
    "PythonTools": ("agno.tools.python", "PythonTools"),
    "ShellTools": ("agno.tools.shell", "ShellTools"),
}


def build_tool(tool: Tool) -> Any:
    """Instantiate an Agno tool from a stored Tool record."""
    config = tool.config or {}
    if tool.kind == "builtin":
        return _build_builtin(tool.reference, config)
    if tool.kind == "custom":
        return _build_custom(tool.reference, config)
    raise ValidationError(f"Unsupported tool kind: {tool.kind}")


def _build_builtin(reference: str, config: dict) -> Any:
    """Resolve a built-in Agno tool by its reference name."""
    if reference in BUILTIN_TOOLS:
        module_name, class_name = BUILTIN_TOOLS[reference]
    elif "." in reference:
        module_name, class_name = reference.rsplit(".", 1)
    else:
        raise ValidationError(f"Unknown built-in tool reference: {reference}")

    try:
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name)
    except (ImportError, AttributeError) as exc:
        raise ValidationError(f"Cannot load tool '{reference}': {exc}") from exc
    return cls(**config)


def _build_custom(reference: str, config: dict) -> Any:
    """Resolve a user-defined callable from a dotted path."""
    if "." not in reference:
        raise ValidationError(
            "Custom tool reference must be a dotted path 'module.function_name'"
        )
    module_name, attr = reference.rsplit(".", 1)
    try:
        module = importlib.import_module(module_name)
        func = getattr(module, attr)
    except (ImportError, AttributeError) as exc:
        raise ValidationError(f"Cannot load custom tool '{reference}': {exc}") from exc
    return func(**config) if config and callable(func) and _accepts_kwargs(func) else func


def _accepts_kwargs(func: Any) -> bool:
    """Return True when ``func`` is a factory that should be called with config."""
    return getattr(func, "__is_factory__", False) is True
