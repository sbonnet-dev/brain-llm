#!/usr/bin/env python3
"""Bootstrap brain-llm from a YAML configuration file.

Usage:
    python scripts/init-agents.py [--config PATH] [--base-url URL]

Defaults:
    --config   scripts/agents-config.yaml
    --base-url http://localhost:8000

The script is idempotent: every resource is looked up by name first and only
created when absent.  Providers → models → agents → teams are processed in
dependency order.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import httpx
import yaml

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
_BLUE = "\033[1;34m"
_GREEN = "\033[1;32m"
_RED = "\033[1;31m"
_RESET = "\033[0m"


def _log(msg: str) -> None:
    print(f"{_BLUE}[init-agents]{_RESET} {msg}")


def _ok(msg: str) -> None:
    print(f"{_GREEN}[ok]{_RESET} {msg}")


def _err(msg: str) -> None:
    print(f"{_RED}[error]{_RESET} {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

class APIClient:
    def __init__(self, base_url: str) -> None:
        self._client = httpx.Client(base_url=base_url.rstrip("/"), timeout=30)

    def get(self, path: str) -> Any:
        r = self._client.get(path)
        r.raise_for_status()
        return r.json()

    def post(self, path: str, payload: dict) -> Any:
        r = self._client.post(path, json=payload)
        r.raise_for_status()
        return r.json()

    def close(self) -> None:
        self._client.close()


# ---------------------------------------------------------------------------
# Resource helpers
# ---------------------------------------------------------------------------

def _find_by_name(items: list[dict], name: str) -> dict | None:
    return next((i for i in items if i.get("name") == name), None)


def ensure_provider(api: APIClient, cfg: dict) -> int:
    """Return the id of the named provider, creating it if needed."""
    providers = api.get("/api/v1/providers")
    existing = _find_by_name(providers, cfg["name"])
    if existing:
        _log(f"Provider '{cfg['name']}' already exists (id={existing['id']})")
        return existing["id"]

    _log(f"Creating provider '{cfg['name']}' ({cfg['provider_type']} @ {cfg['base_url']})")
    payload = {
        "name": cfg["name"],
        "provider_type": cfg["provider_type"],
        "base_url": cfg["base_url"],
    }
    for opt in ("api_key", "default_model", "description"):
        if opt in cfg:
            payload[opt] = cfg[opt]

    created = api.post("/api/v1/providers", payload)
    _ok(f"Provider '{cfg['name']}' created (id={created['id']})")
    return created["id"]


def ensure_model(api: APIClient, cfg: dict, provider_id_map: dict[str, int]) -> int:
    """Return the id of the named model, creating it if needed."""
    provider_name = cfg["provider"]
    provider_id = provider_id_map.get(provider_name)
    if provider_id is None:
        _err(f"Model '{cfg['name']}': unknown provider '{provider_name}'")

    models = api.get("/api/v1/models")
    existing = next(
        (m for m in models if m["name"] == cfg["name"] and m["provider_id"] == provider_id),
        None,
    )
    if existing:
        _log(f"Model '{cfg['name']}' already exists (id={existing['id']})")
        return existing["id"]

    _log(f"Registering model '{cfg['name']}' ({cfg['model_type']}) on provider '{provider_name}'")
    payload = {
        "name": cfg["name"],
        "model_type": cfg["model_type"],
        "provider_id": provider_id,
    }
    if "description" in cfg:
        payload["description"] = cfg["description"]

    created = api.post("/api/v1/models", payload)
    _ok(f"Model '{cfg['name']}' created (id={created['id']})")
    return created["id"]


def _resolve_model_id(
    cfg_model: str,
    cfg_provider: str,
    model_id_map: dict[tuple[str, str], int],
) -> int:
    key = (cfg_model, cfg_provider)
    mid = model_id_map.get(key)
    if mid is None:
        _err(
            f"Cannot resolve model '{cfg_model}' on provider '{cfg_provider}'. "
            "Make sure both are declared in the 'models' and 'providers' sections."
        )
    return mid  # type: ignore[return-value]


def ensure_agent(
    api: APIClient,
    cfg: dict,
    model_id_map: dict[tuple[str, str], int],
) -> int:
    """Return the id of the named agent, creating it if needed."""
    agents = api.get("/api/v1/agents")
    existing = _find_by_name(agents, cfg["name"])
    if existing:
        _log(f"Agent '{cfg['name']}' already exists (id={existing['id']})")
        return existing["id"]

    model_id = _resolve_model_id(cfg["model"], cfg["provider"], model_id_map)
    _log(f"Creating agent '{cfg['name']}'")
    payload: dict[str, Any] = {
        "name": cfg["name"],
        "model_id": model_id,
    }
    for opt in ("role", "description", "instructions", "tool_ids", "knowledge_ids", "extra_config"):
        if opt in cfg:
            payload[opt] = cfg[opt]

    created = api.post("/api/v1/agents", payload)
    _ok(f"Agent '{cfg['name']}' created (id={created['id']})")
    return created["id"]


def ensure_team(
    api: APIClient,
    cfg: dict,
    model_id_map: dict[tuple[str, str], int],
    agent_id_map: dict[str, int],
) -> int:
    """Return the id of the named team, creating it if needed."""
    teams = api.get("/api/v1/teams")
    existing = _find_by_name(teams, cfg["name"])
    if existing:
        _log(f"Team '{cfg['name']}' already exists (id={existing['id']})")
        return existing["id"]

    _log(f"Creating team '{cfg['name']}'")
    payload: dict[str, Any] = {"name": cfg["name"]}

    for opt in ("description", "mode", "instructions", "tool_ids", "knowledge_ids", "extra_config"):
        if opt in cfg:
            payload[opt] = cfg[opt]

    if "model" in cfg and "provider" in cfg:
        payload["model_id"] = _resolve_model_id(cfg["model"], cfg["provider"], model_id_map)

    if "members" in cfg:
        member_ids = []
        for member_name in cfg["members"]:
            mid = agent_id_map.get(member_name)
            if mid is None:
                _err(f"Team '{cfg['name']}': unknown member agent '{member_name}'")
            member_ids.append(mid)
        payload["member_agent_ids"] = member_ids

    created = api.post("/api/v1/teams", payload)
    _ok(f"Team '{cfg['name']}' created (id={created['id']})")
    return created["id"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--config",
        default=str(Path(__file__).parent / "agents-config.yaml"),
        help="Path to the YAML configuration file (default: scripts/agents-config.yaml)",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="brain-llm API base URL (default: http://localhost:8000)",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        _err(f"Config file not found: {config_path}")

    with config_path.open() as fh:
        config = yaml.safe_load(fh) or {}

    api = APIClient(args.base_url)

    # 1. Health check
    _log(f"Checking API at {args.base_url}/health …")
    try:
        api.get("/health")
    except httpx.HTTPError as exc:
        _err(f"API not reachable: {exc}")
    _log("API is up.")

    # 2. Providers
    provider_id_map: dict[str, int] = {}
    for pcfg in config.get("providers") or []:
        provider_id_map[pcfg["name"]] = ensure_provider(api, pcfg)

    # 3. Models  — keyed by (name, provider_name) to allow same model name on
    #              different providers without collision.
    model_id_map: dict[tuple[str, str], int] = {}
    for mcfg in config.get("models") or []:
        key = (mcfg["name"], mcfg["provider"])
        model_id_map[key] = ensure_model(api, mcfg, provider_id_map)

    # 4. Agents
    agent_id_map: dict[str, int] = {}
    for acfg in config.get("agents") or []:
        agent_id_map[acfg["name"]] = ensure_agent(api, acfg, model_id_map)

    # 5. Teams
    team_id_map: dict[str, int] = {}
    for tcfg in config.get("teams") or []:
        team_id_map[tcfg["name"]] = ensure_team(api, tcfg, model_id_map, agent_id_map)

    api.close()

    print()
    print("All resources are ready.")
    if agent_id_map:
        first_agent_id = next(iter(agent_id_map.values()))
        print(f"\nTry it out:\n")
        print(f"  curl -X POST {args.base_url}/api/v1/agents/{first_agent_id}/run \\")
        print(f"       -H 'Content-Type: application/json' \\")
        print(f"       -d '{{\"message\": \"Hello, who are you?\"}}'")


if __name__ == "__main__":
    main()
