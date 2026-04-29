"""Instantiate Agno tools from stored Tool records."""

import importlib
import importlib.util
import inspect
import sys
import uuid
from typing import Any

from app.core.exceptions import ValidationError
from app.core.logging_config import get_logger
from app.models.tool import Tool
from app.services.tool_service import tool_source_path

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
    if tool.kind == "builtin":
        return _build_builtin(tool.reference)
    if tool.kind == "custom":
        return _build_custom(tool.reference)
    if tool.kind == "python_file":
        return _build_python_file(tool.id)
    raise ValidationError(f"Unsupported tool kind: {tool.kind}")


def _build_python_file(tool_id: int) -> Any:
    """Load an uploaded .py file and return an Agno Toolkit instance.

    The file must define either a module-level ``toolkit`` attribute that is
    already a Toolkit instance, or at least one ``agno.tools.Toolkit``
    subclass — the first such subclass is instantiated with no arguments.
    """
    path = tool_source_path(tool_id)
    if not path.exists():
        raise ValidationError(f"Source file for tool id={tool_id} is missing on disk")

    module_name = f"brain_llm_tool_{tool_id}_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ValidationError(f"Cannot load Python tool file at {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(module_name, None)
        raise ValidationError(f"Error executing tool file {path.name}: {exc}") from exc

    try:
        from agno.tools import Toolkit
    except ImportError as exc:
        raise ValidationError(f"agno.tools.Toolkit unavailable: {exc}") from exc

    instance = getattr(module, "toolkit", None)
    if isinstance(instance, Toolkit):
        return instance

    for _, obj in inspect.getmembers(module, inspect.isclass):
        if obj.__module__ != module.__name__:
            continue
        if issubclass(obj, Toolkit) and obj is not Toolkit:
            try:
                return obj()
            except Exception as exc:
                raise ValidationError(
                    f"Failed to instantiate toolkit class {obj.__name__}: {exc}"
                ) from exc

    raise ValidationError(
        f"No agno Toolkit found in {path.name}: define a `toolkit` instance "
        "or a Toolkit subclass."
    )


def _build_builtin(reference: str) -> Any:
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
    return cls()


def _build_custom(reference: str) -> Any:
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
    return func() if getattr(func, "__is_factory__", False) is True else func
