#!/usr/bin/env python3
"""Bootstrap brain-llm from scripts/agents-config.yaml.

Order of operations: providers → models → knowledges → agents → teams.
Idempotent: every resource is looked up by name first.

Usage:
    python scripts/1-init-agents.py [--config PATH] [--base-url URL]
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
    kb_create_payload,
    load_config,
    make_loggers,
)

_log, _ok, _warn, _err = make_loggers("init-agents")


class APIClient:
    def __init__(self, base_url: str) -> None:
        self._client = httpx.Client(base_url=base_url.rstrip("/"), timeout=60)

    def get(self, path: str) -> Any:
        r = self._client.get(path)
        r.raise_for_status()
        return r.json()

    def post(self, path: str, payload: dict) -> Any:
        r = self._client.post(path, json=payload)
        if r.status_code >= 400:
            _err(f"POST {path} failed ({r.status_code}): {r.text}")
        return r.json()

    def put(self, path: str, payload: dict) -> Any:
        r = self._client.put(path, json=payload)
        if r.status_code >= 400:
            _err(f"PUT {path} failed ({r.status_code}): {r.text}")
        return r.json()

    def close(self) -> None:
        self._client.close()


def ensure_provider(api: APIClient, cfg: dict) -> int:
    providers = api.get("/api/v1/providers")
    existing = find_by_name(providers, cfg["name"])
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


def ensure_knowledge(
    api: APIClient,
    cfg: dict,
    model_id_map: dict[tuple[str, str], int],
) -> int:
    """Create or update a knowledge base (KB) declared in the YAML."""
    payload = kb_create_payload(cfg)
    embedder_ref = cfg.get("embedder_model")
    if embedder_ref:
        payload["embedder_model_id"] = _resolve_model_id(
            embedder_ref["model"], embedder_ref["provider"], model_id_map
        )

    name = payload["name"]
    kbs = api.get("/api/v1/knowledge/bases")
    existing = find_by_name(kbs, name)

    if existing:
        # Update if embedder_model_id/vector_db drifted; the API uses PUT for KBs.
        diff = {k: v for k, v in payload.items() if existing.get(k) != v and k != "name"}
        if diff:
            _log(f"Updating KB '{name}' fields: {sorted(diff)}")
            api.put(f"/api/v1/knowledge/bases/{existing['id']}", diff)
            _ok(f"KB '{name}' updated (id={existing['id']})")
        else:
            _log(f"KB '{name}' already exists (id={existing['id']})")
        return existing["id"]

    _log(f"Creating KB '{name}'")
    created = api.post("/api/v1/knowledge/bases", payload)
    _ok(f"KB '{name}' created (id={created['id']}, collection={created.get('collection_name')})")
    return created["id"]


def _resolve_model_id(
    cfg_model: str,
    cfg_provider: str,
    model_id_map: dict[tuple[str, str], int],
) -> int:
    mid = model_id_map.get((cfg_model, cfg_provider))
    if mid is None:
        _err(
            f"Cannot resolve model '{cfg_model}' on provider '{cfg_provider}'. "
            "Make sure both are declared in 'models' and 'providers'."
        )
    return mid  # type: ignore[return-value]


def _resolve_knowledge_ids(
    cfg: dict,
    knowledge_id_map: dict[str, int],
) -> list[int] | None:
    """Return knowledge_ids resolved from either 'knowledges' (names) or 'knowledge_ids'."""
    if "knowledges" in cfg:
        ids = []
        for name in cfg["knowledges"]:
            kid = knowledge_id_map.get(name)
            if kid is None:
                _err(f"Unknown knowledge '{name}' — declare it under 'knowledges:' first")
            ids.append(kid)
        return ids
    if "knowledge_ids" in cfg:
        return list(cfg["knowledge_ids"])
    return None


def ensure_agent(
    api: APIClient,
    cfg: dict,
    model_id_map: dict[tuple[str, str], int],
    knowledge_id_map: dict[str, int],
) -> int:
    agents = api.get("/api/v1/agents")
    existing = find_by_name(agents, cfg["name"])
    if existing:
        _log(f"Agent '{cfg['name']}' already exists (id={existing['id']})")
        return existing["id"]

    model_id = _resolve_model_id(cfg["model"], cfg["provider"], model_id_map)
    payload: dict[str, Any] = {"name": cfg["name"], "model_id": model_id}
    for opt in ("role", "description", "instructions", "tool_ids", "extra_config"):
        if opt in cfg:
            payload[opt] = cfg[opt]

    knowledge_ids = _resolve_knowledge_ids(cfg, knowledge_id_map)
    if knowledge_ids is not None:
        payload["knowledge_ids"] = knowledge_ids

    _log(f"Creating agent '{cfg['name']}'")
    created = api.post("/api/v1/agents", payload)
    _ok(f"Agent '{cfg['name']}' created (id={created['id']})")
    return created["id"]


def ensure_team(
    api: APIClient,
    cfg: dict,
    model_id_map: dict[tuple[str, str], int],
    agent_id_map: dict[str, int],
    knowledge_id_map: dict[str, int],
) -> int:
    teams = api.get("/api/v1/teams")
    existing = find_by_name(teams, cfg["name"])
    if existing:
        _log(f"Team '{cfg['name']}' already exists (id={existing['id']})")
        return existing["id"]

    payload: dict[str, Any] = {"name": cfg["name"]}
    for opt in ("description", "mode", "instructions", "tool_ids", "extra_config"):
        if opt in cfg:
            payload[opt] = cfg[opt]

    if "model" in cfg and "provider" in cfg:
        payload["model_id"] = _resolve_model_id(cfg["model"], cfg["provider"], model_id_map)

    knowledge_ids = _resolve_knowledge_ids(cfg, knowledge_id_map)
    if knowledge_ids is not None:
        payload["knowledge_ids"] = knowledge_ids

    if "members" in cfg:
        member_ids = []
        for member_name in cfg["members"]:
            mid = agent_id_map.get(member_name)
            if mid is None:
                _err(f"Team '{cfg['name']}': unknown member agent '{member_name}'")
            member_ids.append(mid)
        payload["member_agent_ids"] = member_ids

    _log(f"Creating team '{cfg['name']}'")
    created = api.post("/api/v1/teams", payload)
    _ok(f"Team '{cfg['name']}' created (id={created['id']})")
    return created["id"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()

    try:
        config, _ = load_config(args.config)
    except FileNotFoundError as exc:
        _err(str(exc))

    api = APIClient(args.base_url)

    _log(f"Checking API at {args.base_url}/health …")
    try:
        api.get("/health")
    except httpx.HTTPError as exc:
        _err(f"API not reachable: {exc}")

    provider_id_map: dict[str, int] = {}
    for pcfg in config.get("providers") or []:
        provider_id_map[pcfg["name"]] = ensure_provider(api, pcfg)

    model_id_map: dict[tuple[str, str], int] = {}
    for mcfg in config.get("models") or []:
        model_id_map[(mcfg["name"], mcfg["provider"])] = ensure_model(api, mcfg, provider_id_map)

    knowledge_id_map: dict[str, int] = {}
    for kcfg in config.get("knowledges") or []:
        knowledge_id_map[kcfg["name"]] = ensure_knowledge(api, kcfg, model_id_map)

    agent_id_map: dict[str, int] = {}
    for acfg in config.get("agents") or []:
        agent_id_map[acfg["name"]] = ensure_agent(api, acfg, model_id_map, knowledge_id_map)

    for tcfg in config.get("teams") or []:
        ensure_team(api, tcfg, model_id_map, agent_id_map, knowledge_id_map)

    api.close()
    print()
    _ok("All resources are ready.")


if __name__ == "__main__":
    main()
