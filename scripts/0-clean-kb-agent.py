#!/usr/bin/env python3
"""Delete all resources declared in agents-config.yaml (agents, KBs, models).

Deletion order respects referential integrity:
  teams → agents → KBs → models

Providers are intentionally kept (they are infrastructure-level config).
Use --providers to also delete them.

Typical workflow:

    python scripts/0-clean-kb-agent.py
    python scripts/1-init-agents.py
    python scripts/2-init-kb-agent.py
    python scripts/3-test-kb-agent.py

Usage:
    python scripts/0-clean-kb-agent.py [--config PATH] [--base-url URL]
                                       [--providers]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from _shared import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    find_by_name,
    load_config,
    make_loggers,
)

_log, _ok, _warn, _err = make_loggers("clean")


def _get(client: httpx.Client, path: str) -> Any:
    r = client.get(path)
    r.raise_for_status()
    return r.json()


def _delete(client: httpx.Client, path: str, label: str) -> bool:
    r = client.delete(path)
    if r.status_code == 404:
        _warn(f"{label} — already gone (404)")
        return False
    if r.status_code >= 400:
        _err(f"DELETE {path} failed ({r.status_code}): {r.text}")
    _ok(f"Deleted {label}")
    return True


def delete_teams(client: httpx.Client, config: dict) -> None:
    declared = [t["name"] for t in (config.get("teams") or [])]
    if not declared:
        return
    teams = _get(client, "/api/v1/teams")
    for name in declared:
        existing = find_by_name(teams, name)
        if not existing:
            _warn(f"Team '{name}' — not found, skipping")
            continue
        _delete(client, f"/api/v1/teams/{existing['id']}", f"team '{name}' (id={existing['id']})")


def delete_agents(client: httpx.Client, config: dict) -> None:
    declared = [a["name"] for a in (config.get("agents") or [])]
    agents = _get(client, "/api/v1/agents")
    for name in declared:
        existing = find_by_name(agents, name)
        if not existing:
            _warn(f"Agent '{name}' — not found, skipping")
            continue
        _delete(client, f"/api/v1/agents/{existing['id']}", f"agent '{name}' (id={existing['id']})")


def delete_kbs(client: httpx.Client, config: dict) -> None:
    declared = [k["name"] for k in (config.get("knowledges") or [])]
    kbs = _get(client, "/api/v1/knowledge/bases")
    for name in declared:
        existing = find_by_name(kbs, name)
        if not existing:
            _warn(f"KB '{name}' — not found, skipping")
            continue
        _delete(
            client,
            f"/api/v1/knowledge/bases/{existing['id']}",
            f"KB '{name}' (id={existing['id']}, collection={existing.get('collection_name')}) — Qdrant + files removed",
        )


def delete_models(client: httpx.Client, config: dict) -> None:
    declared = [m["name"] for m in (config.get("models") or [])]
    models = _get(client, "/api/v1/models")
    for name in declared:
        existing = find_by_name(models, name)
        if not existing:
            _warn(f"Model '{name}' — not found, skipping")
            continue
        _delete(client, f"/api/v1/models/{existing['id']}", f"model '{name}' (id={existing['id']})")


def delete_providers(client: httpx.Client, config: dict) -> None:
    declared = [p["name"] for p in (config.get("providers") or [])]
    providers = _get(client, "/api/v1/providers")
    for name in declared:
        existing = find_by_name(providers, name)
        if not existing:
            _warn(f"Provider '{name}' — not found, skipping")
            continue
        _delete(client, f"/api/v1/providers/{existing['id']}", f"provider '{name}' (id={existing['id']})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--providers", action="store_true", help="Also delete providers.")
    args = parser.parse_args()

    try:
        config, _ = load_config(args.config)
    except FileNotFoundError as exc:
        _err(str(exc))

    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=60) as client:
        _log(f"Checking API at {args.base_url}/health …")
        try:
            _get(client, "/health")
        except httpx.HTTPError as exc:
            _err(f"API not reachable: {exc}")

        delete_teams(client, config)
        delete_agents(client, config)
        delete_kbs(client, config)
        delete_models(client, config)
        if args.providers:
            delete_providers(client, config)

    print()
    _ok("Done.")


if __name__ == "__main__":
    main()
