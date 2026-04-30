"""Shared helpers for scripts/{0,1,2,3}-*.py.

All four scripts read scripts/agents-config.yaml as their single source of
truth for KB names, embedder configuration, default agent, etc. Keep this
module dependency-light — only the standard library + PyYAML.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).parent / "agents-config.yaml"

_BLUE = "\033[1;34m"
_GREEN = "\033[1;32m"
_YELLOW = "\033[1;33m"
_RED = "\033[1;31m"
_RESET = "\033[0m"


def make_loggers(tag: str):
    def _log(msg: str) -> None:
        print(f"{_BLUE}[{tag}]{_RESET} {msg}")

    def _ok(msg: str) -> None:
        print(f"{_GREEN}[ok]{_RESET} {msg}")

    def _warn(msg: str) -> None:
        print(f"{_YELLOW}[warn]{_RESET} {msg}")

    def _err(msg: str) -> None:
        print(f"{_RED}[error]{_RESET} {msg}", file=sys.stderr)
        sys.exit(1)

    return _log, _ok, _warn, _err


def load_config(path: str | Path | None = None) -> tuple[dict, Path]:
    """Load the YAML config and return ``(config, resolved_path)``."""
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {cfg_path}")
    with cfg_path.open() as fh:
        return yaml.safe_load(fh) or {}, cfg_path


def find_by_name(items: list[dict], name: str) -> dict | None:
    return next((i for i in items if i.get("name") == name), None)


def first_kb(config: dict) -> dict:
    """Return the first KB declared in the config (or raise)."""
    kbs = config.get("knowledges") or []
    if not kbs:
        raise ValueError("No 'knowledges' entries declared in config")
    return kbs[0]


def kb_agent(config: dict) -> dict:
    """Return the agent referenced by ``test.agent`` (default 'KBAssistant')."""
    name = (config.get("test") or {}).get("agent", "KBAssistant")
    agents = config.get("agents") or []
    match = find_by_name(agents, name)
    if match is None:
        raise ValueError(f"Agent '{name}' not declared in config")
    return match


def resolve_samples_dir(config_path: Path, kb_cfg: dict) -> Path:
    """Resolve ``kb.samples_dir`` relative to the YAML file's location."""
    raw = kb_cfg.get("samples_dir")
    if not raw:
        return config_path.parent / "kb-samples"
    p = Path(raw)
    return p if p.is_absolute() else config_path.parent / p


def kb_create_payload(kb_cfg: dict) -> dict[str, Any]:
    """Convert a YAML knowledges[] entry into a KnowledgeCreate body.

    The caller is responsible for resolving the YAML ``embedder_model``
    reference (``{model, provider}``) to an ``embedder_model_id`` before
    POSTing — that lookup needs the model_id_map which lives in 1-init-agents.
    """
    payload: dict[str, Any] = {"name": kb_cfg["name"]}
    for key in ("description", "collection_name", "vector_db"):
        if key in kb_cfg and kb_cfg[key] is not None:
            payload[key] = kb_cfg[key]
    return payload
